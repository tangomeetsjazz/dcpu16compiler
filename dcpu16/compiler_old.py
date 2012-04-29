import ply.lex as lex
import ply.yacc as yacc
import sys

# Lexer
reserved = {
   'function' : "FUNCTION",
   'return' : "RETURN",
   'if' : 'IF',
   'else' : 'ELSE',
   'while' : 'WHILE',
   'for' : 'FOR',
   'screen' : 'SCREEN',
   'SCREEN' : 'SCREEN',
}

tokens = (
    "MOD", "PLUS", "MINUS", "TIMES", "DIVIDE",
    "COMPARISON", "AND", "OR",
    "FUNCTION", "RETURN", "IF", "ELSE", "WHILE", "FOR",
    "SCREEN", "NAME", "NUMBER"
)

literals = [';', '=', '(', ')', '{', '}', '[', ']']

t_MOD = "%"
t_PLUS = "\+"
t_MINUS = "-"
t_TIMES = "\*"
t_DIVIDE = "/"
t_COMPARISON = r"[><!=]="
t_AND = "&&"
t_OR = "\|\|"
t_FUNCTION = "function"
t_RETURN = "return"
t_IF = "if"
t_ELSE = "else"
t_WHILE = "while"
t_FOR = "for"
t_SCREEN = r"SCREEN|screen"

def t_NAME(t):
    r"[_a-zA-Z][_a-zA-Z0-9]*"
    t.type = reserved.get(t.value, "NAME")
    return t

def t_NUMBER(t):
    r"\d+"
    t.value = int(t.value)
    return t

t_ignore = " \t\n"

def t_error(t):
    raise Exception("Syntax error on token: %s" % (t.value))

# Parser

VARIABLE_ADDRESS_RANGE = (0x2000, 0x7000)

class Variable:
    def __init__(self, name, address, context):
        self.name = name
        self.address = address
        self.context = context

    def toMemoryAddress(self):
        hexStr = hex(VARIABLE_ADDRESS_RANGE[0] + self.address)
        while hexStr < 6:
            hexStr = hexStr[0:2] + "0" + hexStr[2:]
        return "[" + hexStr + "]"

class Context:
    def __init__(self, parent = None):
        self.parent = parent
        self.varsByAddress = {}
        self.varsByName = {}
    
    def startChildContext(self):
        return Context(self)
    
    def getNextAddress(self):
        if self.parent:
            return self.parent.getNextAddress()
        
        for i in range(0, VARIABLE_ADDRESS_RANGE[1] - VARIABLE_ADDRESS_RANGE[0]):
            if i not in self.varsByAddress:
                return i
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

precedence = (
    ('right', '='),
    ('left', 'OR'),
    ('left', 'AND'),
    ('left', 'COMPARISON'),
    ('left', 'MOD'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
)

def p_program(t):
    """program : lines"""
    t[0] = t[1]
    
def p_lines(t):
    """lines : 
             | lines line
    """
    try:
        t[0] = ("%s\n%s" % (t[1], t[2])).strip()
    except:
        t[0] = ""
    
def p_line(t):
    """line : construct
            | control
            | statement ';'
            | expr ';'
    """
    t[0] = t[1]

def p_construct(t):
    """construct : function"""
    t[0] = t[1]

def p_function(t):
    """function : start_context FUNCTION NAME '(' ')' '{' lines return '}' end_context"""
    
    if t[3] in ["start", "end"]:
        t[0] = """
:%s
%s
""".strip() % (t[3], t[7])
    else:
        t[0] = """
:%s
%s
%s
""".strip() % (t[3], t[7], t[8])

def p_return(t):
    """return :
              | RETURN variable ';'
              | RETURN ';'
    """
    
    if 2 in t and t[2] != ";":
        t[0] = """
set a, %s
set PC, POP
""".strip() % (t[2],)
    else:
        t[0] = """
set PC, POP
""".strip()

def p_control(t):
    """control : while_loop
               | for_loop
               | if_control
    """
    t[0] = t[1]

def p_while_loop(t):
    """while_loop : start_context WHILE '(' clause ')' '{' lines '}' end_context"""
    tagName = t.lexer.program.getUniqueTag("loop")
    t[0] = """
:%sstart
%s
ifn a, 1
set PC, %send
%s
:%send
""".strip() % (tagName, t[4], tagName, t[7], tagName)

def p_for_loop(t):
    """for_loop : start_context FOR '(' statement ';' clause ';' statement ')' '{' lines '}' end_context"""
    tagName = t.lexer.program.getUniqueTag("loop")
    t[0] = """
%s
:%sstart
%s
ifn a, 1
set PC, %send
%s
%s
set PC, %sstart
:%send
""".strip() % (t[4], tagName, t[6], tagName, t[11], t[8], tagName, tagName)

def p_if_control_plain(t):
    """if_control : IF '(' clause ')' '{' start_context lines end_context '}'"""
    tagName = t.lexer.program.getUniqueTag("if")
    t[0] = """
%s
ifn a, 1
set PC, %send
%s
:%send
""".strip() % (t[3], tagName, t[7], tagName)

def p_if_control_with_else(t):
    """if_control : IF '(' clause ')' '{' start_context lines end_context '}' ELSE '{' start_context lines end_context '}'"""
    
    tagName = t.lexer.program.getUniqueTag("if")
    t[0] = """
%s
ifn a, 1
set PC, %selse
%s
:%selse
%s
""".strip() % (t[3], tagName, t[7], tagName, t[13])

def p_if_control_with_else_if(t):
    """if_control : IF '(' clause ')' '{' start_context lines end_context '}' ELSE if_control"""
    
    tagName = t.lexer.program.getUniqueTag("if")
    t[0] = """
%s
ifn a, 1
set PC, %selseif
%s
set PC, %send
:%selseif
%s
:%send
""".strip() % (t[3], tagName, t[7], tagName, tagName, t[11], tagName)

def p_statement(t):
    """statement : assignment"""
    t[0] = t[1]

def p_assignment_regular(t):
    """assignment : variable '=' expr"""
    t[0] = """
%s
set %s, a
""".strip() % (t[3], t[1])

def p_assignment_screen(t):
    """assignment : SCREEN '[' operation ']' '=' operation"""
    t[0] = """
%s
set b, a
add b, 0x8000
%s
set [b], a
""".strip() % (t[3], t[6])

def p_expr(t):
    """expr : function_call
            | return
            | clause
            | operation
    """
    t[0] = t[1]

def p_function_call(t):
    """function_call : NAME '(' ')'"""
    if t[1] == "exit":
        t[0] = "set PC, end"
    else:
        t[0] = "jsr %s" % (t[1],)

def p_clause_comparison(t):
    """clause : value COMPARISON value"""
    
    str = """
set a, 0
%(comp)s %(val1)s, %(val2)s
set a, 1
""".strip()

    comp = None
    if t[2] == "==":
        comp = "ife"
    elif t[2] == "!=":
        comp = "ifn"
    elif t[2] == ">=":
        comp = "ifg"
    elif t[2] == "<=":
        comp = "ifl"
    
    if t[2] in (">=", "<="):
        str += "\n" + """
ife %(val1)s, %(val2)s
set a, 1
""".strip()
    
    t[0] = str.strip() % {'comp':comp, 'val1':t[1], 'val2':t[3]}

def p_clause_logic(t):
    """clause : clause logic clause"""
    
    if t[2] == "&&":
        val = 0
    elif t[2] == "||":
        val = 1
    
    tagName = t.lexer.program.getUniqueTag("skip")
    t[0] = """
%s
ife a, %d
set PC, %send
%s
:%send
""".strip() % (t[1], val, tagName, t[3], tagName)

def p_operation_simplify(t):
    """operation : '(' operation ')'
                 | value
    """
    if 2 in t:
        t[0] = t[2]
    else:
        t[0] = "set a, %s" % (t[1],)

def p_operation_execute(t):
    """operation : operation TIMES operation
                 | operation DIVIDE operation
                 | operation PLUS operation
                 | operation MINUS operation
                 | operation MOD operation
    """
    opr = None
    if t[2] == "*":
        opr = "mul"
    elif t[2] == "/":
        opr = "div"
    elif t[2] == "+":
        opr = "add"
    elif t[2] == "-":
        opr = "sub"
    elif t[2] == "%":
        opr = "mod"
    t[0] = """
%s
set b, a
%s
%s b, a
set a, b
""".strip() % (t[1], t[3], opr)

def p_logic(t):
    """logic : AND
             | OR
    """
    t[0] = t[1]

def p_value(t):
    """value : variable
             | NUMBER
    """
    t[0] = t[1]

def p_variable(t):
    """variable : NAME"""
    var = t.lexer.context.getVariable(t[1])
    t[0] = var.toMemoryAddress()

def p_start_context(t):
    """start_context : """
    
    t.lexer.context = t.lexer.context.startChildContext()
    
    t[0] = ""

def p_end_context(t):
    """end_context : """
    
    if t.lexer.context == t.lexer.program:
        raise Exception("Global context cannot be destroyed")
    
    t.lexer.context.destroy()
    t.lexer.context = t.lexer.context.parent
    
    t[0] = ""

def p_error(t):
    raise Exception("Error parsing: %s" % (str(t),))

lexer = lex.lex()
lexer.program = Program()
lexer.context = lexer.program
parser = yacc.yacc()
