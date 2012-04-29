import ast

VARIABLE_ADDRESS_RANGE = (0x2000, 0x7000)

BIN_OP_MAP = {
    "Add" : "add",
    "Sub" : "sub",
    "Mult" : "mul",
    "Div" : "div",
    "Mod" : "mod",
}

BOOL_OP_MAP = {
    "And" : "ifn",
    "Or" : "ife",
}

UNARY_OP_MAP = {
    "Not" : "xor",
}

COMPARE_OP_MAP = {
    "GtE" : ["ifg", "ife"],
    "Gt" : "ifg",
    "LtE" : ["ifl", "ife"],
    "Lt" : "ifl",
    "Eq" : "ife",
}

class Variable:
    def __init__(self, name, address, context):
        self.name = name
        self.address = address
        self.context = context

class Context:
    def __init__(self, parent = None):
        self.parent = parent
        self.varsByAddress = {}
        self.varsByName = {}
    
    def startChildContext(self):
        return Context(self)
    
    def toAddress(self, num):
        address = hex(num)
        while address < 6:
            address = address[0:2] + "0" + address[2:]
        return address
    
    def getNextAddress(self):
        if self.parent:
            return self.parent.getNextAddress()
        
        for num in range(VARIABLE_ADDRESS_RANGE[0], VARIABLE_ADDRESS_RANGE[1] + 1):
            address = self.toAddress(num)
            if address not in self.varsByAddress:
                return address
        raise Exception("Memory exhausted")
    
    def getVariable(self, name, context = None):
        context = context if context else self
        
        if name in self.varsByName:
            localContextVar = None
            for var in self.varsByName[name]:
                if var.context == context:
                    return var
                elif var.context == self:
                    localContextVar = var
            if localContextVar is not None:
                return localContextVar
        
        if self.parent:
            var = self.parent.getVariable(name, context)
            if var.context == self:
                self.addVariable(var)
            return var
        
        address = self.getNextAddress()
        var = Variable(name, address, context)
        self.addVariable(var)
        return var
    
    def addVariable(self, var):
        self.varsByAddress[var.address] = var
        if var.name not in self.varsByName:
            self.varsByName[var.name] = []
        self.varsByName[var.name].append(var)
    
    def removeVariable(self, var):
        if self.parent:
            self.parent.removeVariable(var)
        if var.address in self.varsByAddress:
            del self.varsByAddress[var.address]
        if var.name in self.varsByName:
            self.varsByName[var.name].remove(var)
    
    def removeAddress(self, address):
        if self.parent:
            self.parent.removeAddress(var)
        if address in self.varsByAddress:
            var = self.varsByAddress[address]
            if var.name in self.varsByName:
                self.varsByName[var.name].remove(var)
            del self.varsByAddress[address]
    
    def destroy(self):
        if not self.parent:
            return
        
        for name, vars in self.varsByName.iteritems():
            for var in vars:
                self.parent.removeVariable(var)
        
        self.varsByAddress = {}
        self.varsByName = {}

class Program(Context):
    def __init__(self):
        Context.__init__(self)
        
        self.uniqueId = 0
        
    def getUniqueId(self):
        self.uniqueId += 1
        return self.uniqueId

    def getUniqueTag(self, prefix):
        return "%s%d" % (prefix, self.getUniqueId())
    
    def getUniqueAddress(self):
        var = self.getVariable(str(self.getUniqueId()))
        return var.address

class DCPU16AssemblyProducer(ast.NodeVisitor):
    def __init__(self, program):
        ast.NodeVisitor.__init__(self)
        
        self.program = program
        self.context = program
        self.code = ""
    
    def getOpMapValue(self, map, node, key = "op", index = None):
        op = getattr(node, key)
        if index is not None:
            op = op[index]
        opName = type(op).__name__
        if opName not in map:
            raise Exception("Unknown operation %s on line %s column %s" % (opName, node.lineno, node.col_offset))
        return map[opName]
    
    def startContext(self):
        self.context = self.context.startChildContext()
    
    def endContext(self):
        self.context.destroy()
        self.context = self.context.parent
    
    def getVariableAddress(self, name):
        if name.lower() == "screen":
            return "0x8000"
        return self.context.getVariable(name).address
    
    def visit_Module(self, node):
        code = ""
        for child in node.body:
            subCode = self.visit(child)
            if subCode:
                code += "\n" + subCode
        return code.strip()
    
    def visit_FunctionDef(self, node):
        code = ":%s" % (node.name,)
        for child in node.body:
            subCode = self.visit(child)
            if subCode:
                code += "\n" + subCode
        return code
    
    def visit_Return(self, node):
        code = self.visitForValue(node.value)
        code += "\nset PC, POP"
        return code
    
    def visit_Call(self, node):
        return "jsr %s" % (node.func.id,) if node.func.id != "exit" else "set PC, end"
    
    def visit_If(self, node):
        tagName = self.program.getUniqueTag("if")
        code = self.visitForValue(node.test)
        code += "\nifn a, 1"
        code += "\nset PC, %selse" % (tagName,)
        for child in node.body:
            code += "\n" + self.visit(child)
        code += "\nset PC, %send" % (tagName,)
        code += "\n:%selse" % (tagName,)
        for child in node.orelse:
            code += "\n" + self.visit(child)
        code += "\n:%send" % (tagName,)
        return code
    
    def visit_Assign(self, node):
        uniqueAddress = self.program.getUniqueAddress()
        
        code = self.visitForValue(node.value)
        code += "\nset [%s], a" % (uniqueAddress,)
        for target in node.targets:
            code += "\n" + self.visitForReference(target)
            code += "\nset [a], [%s]" % (uniqueAddress,)
            
        self.program.removeAddress(uniqueAddress)
        
        return code
    
    def visit_BoolOp(self, node):
        opValue = self.getOpMapValue(BOOL_OP_MAP, node)
        tagName = self.program.getUniqueTag("boolop")
        for value in node.values:
            code = self.visitForValue(value)
            code += "\n%s a, 1" % (opValue,)
            code += "\nset PC, %sskip" % (tagName,)
        code += "\n:%sskip" % (tagName,)
        return code
        
    def visit_UnaryOp(self, node):
        opValue = self.getOpMapValue(UNARY_OP_MAP, node)
        
        code = self.visitForValue(node.operand)
        code += "\n%s a, 1" % (opValue,)
        return code
    
    def visit_Compare(self, node):
        uniqueAddress1 = self.program.getUniqueAddress()
        uniqueAddress2 = self.program.getUniqueAddress()
        
        code = self.visitForValue(node.left)
        code += "\nset [%s], a" % (uniqueAddress1,)
        for i in range(0, len(node.ops)):
            opValue = self.getOpMapValue(COMPARE_OP_MAP, node, "ops", i)
            if not isinstance(opValue, list):
                opValue = [opValue]
            
            code += "\n" + self.visitForValue(node.comparators[i])
            code += "\nset [%s], a" % (uniqueAddress2,)
            for opStr in opValue:
                code += "\n%s [%s], [%s]\nset a, 1" % (opStr, uniqueAddress1, uniqueAddress2)
        
        self.program.removeAddress(uniqueAddress1)
        self.program.removeAddress(uniqueAddress2)
        
        return code
    
    def visit_Expr(self, node):
        return self.visitForValue(node.value)
    
    def visit_BinOp(self, node):
        uniqueAddress = self.program.getUniqueAddress()
        opValue = self.getOpMapValue(BIN_OP_MAP, node)
        
        code = self.visitForValue(node.left)
        code += "\nset [%s], a" % (uniqueAddress,)
        code += "\n" + self.visitForValue(node.right)
        code += "\n%s [%s], a" % (opValue, uniqueAddress)
        code += "\nset a, [%s]" % (uniqueAddress,)
        
        self.program.removeAddress(uniqueAddress)
        
        return code
    
    def visit_Subscript(self, node):
        uniqueAddress = self.program.getUniqueAddress()
        
        code = self.visitForValue(node.slice)
        code += "\nset [%s], a" % (uniqueAddress,)
        code += "\n" + self.visitForReference(node.value)
        code += "\nadd a, [%s]" % (uniqueAddress,)
        
        self.program.removeAddress(uniqueAddress)
        
        return code
    
    def visit_Index(self, node):
        return self.visitForValue(node.value)
    
    def visitForReference(self, node):
        if isinstance(node, ast.Name):
            return "set a, %s" % (self.getVariableAddress(node.id),)
        elif isinstance(node, ast.Subscript):
            return self.visit(node)
        else:
            raise Exception("Invalid reference on line %s column %s" % (node.lineno, node.col_offset))
    
    def visitForValue(self, node):
        if isinstance(node, ast.Name):
            return "set a, [%s]" % (self.getVariableAddress(node.id),)
        elif isinstance(node, ast.Num):
            return "set a, %d" % (node.n,)
        else:
            return self.visit(node)
    
    def generic_visit(self, node):
        print type(node).__name__
        print "-" * len(type(node).__name__)
        for attr in dir(node):
            if str(attr)[0] != "_":
                print " " + str(attr)      
        ast.NodeVisitor.generic_visit(self, node)

def parse(str):
    node = ast.parse(str)
    visitor = DCPU16AssemblyProducer(Program())
    print visitor.visit(node)
