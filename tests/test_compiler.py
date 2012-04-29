import unittest
from dcpu16.compiler import VARIABLE_ADDRESS_RANGE, Variable, Context, Program

class VariableTest(unittest.TestCase):
    def testToMemoryAddress(self):
        for address in [235, 504, 12, 1]:
            self.assertEqual(self.getMemoryAddress(address), Variable("var1", address, Context()).toMemoryAddress())
    
    def getMemoryAddress(self, address):
        address += VARIABLE_ADDRESS_RANGE[0]
        hexStr = hex(address)
        while len(hexStr) < 6:
            hexStr = hexStr[0:2] + "0" + hexStr[2:]
        return "[" + hexStr + "]"

class ContextTest(unittest.TestCase):
    def setUp(self):
        pass
    
    def testStartChildContextProducesContextWithCurrentContextAsParent(self):
        parent = Context()
        child = parent.startChildContext()
        self.assertEqual(parent, child.parent)

    def testGetNextMemoryAddressWithoutParentContext(self):
        context = Context()
        
        self.assertEqual(0, context.getNextAddress())
        
        context.varsByAddress[0] = Variable("var1", 0, Context())
        
        self.assertEqual(1, context.getNextAddress())
        
        context.varsByAddress[2] = Variable("var2", 2, Context())
        
        self.assertEqual(1, context.getNextAddress())
        
        context.varsByAddress[1] = Variable("var3", 1, Context())
        
        self.assertEqual(3, context.getNextAddress())
        
        del context.varsByAddress[0]
        
        self.assertEqual(0, context.getNextAddress())
    
    def testGetNextMemoryAddressWithParentContext(self):
        parent = Context()
        context = Context(parent)
        
        self.assertEqual(0, context.getNextAddress())
        
        parent.varsByAddress[0] = Variable("var1", 0, Context())
        
        self.assertEqual(1, context.getNextAddress())
        
        parent.varsByAddress[2] = Variable("var2", 2, Context())
        
        self.assertEqual(1, context.getNextAddress())
        
        parent.varsByAddress[1] = Variable("var3", 1, Context())
        
        self.assertEqual(3, context.getNextAddress())
        
        del parent.varsByAddress[0]
        
        self.assertEqual(0, context.getNextAddress())
    
    def testGetVariableWithoutParentContext(self):
        context = Context()
        
        result1 = context.getVariable("var1")
        result2 = context.getVariable("var2")
        result3 = context.getVariable("var1")
        
        for result in [result1, result2, result3]:
            self.assertFalse(result is None)
        self.assertTrue(result1 == result3)
        self.assertTrue(result1 != result2)
        
    def testGetVariableWithParentContext(self):
        parent = Context()
        context = Context(parent)
        
        result1 = parent.getVariable("var1")
        result2 = context.getVariable("var1")
        result3 = context.getVariable("var2")
        result4 = parent.getVariable("var2")
        
        self.assertTrue(result1 == result2)
        self.assertFalse(result3 == result4)

    def testDestroyWithoutParent(self):
        context = Context()
        
        result = context.getVariable("var1")
        
        context.destroy()
        
        self.assertEqual(result, context.getVariable("var1"))
        
    def testDestroyWithParent(self):
        parent = Context()
        context = Context(parent)
        
        result1 = parent.getVariable("var1")
        result2 = context.getVariable("var2")
        
        context.destroy()
        
        self.assertTrue(result1 == parent.getVariable("var1"))
        self.assertFalse(result2 == context.getVariable("var2"))
    
    def testDestroyAtMultipleLevels(self):
        root = Context()
        context1 = Context(root)
        context2 = Context(context1)
        
        result = context2.getVariable("var2")
        
        context2.destroy()
        
        self.assertFalse(result == context2.getVariable("var2"))
    
class ProgramTest(unittest.TestCase):
    def testGetUniqueId(self):
        program = Program()
        
        self.assertEqual(1, program.getUniqueId())
        self.assertEqual(2, program.getUniqueId())
        self.assertEqual(3, program.getUniqueId())
    
    def testGetUniqueTag(self):
        program = Program()
        
        self.assertEqual("loop1", program.getUniqueTag("loop"))
        self.assertEqual("loop2", program.getUniqueTag("loop"))
        self.assertEqual("skip3", program.getUniqueTag("skip"))
