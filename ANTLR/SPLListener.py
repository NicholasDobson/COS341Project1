# Generated from SPL.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .SPLParser import SPLParser
else:
    from SPLParser import SPLParser

# This class defines a complete listener for a parse tree produced by SPLParser.
class SPLListener(ParseTreeListener):

    # Enter a parse tree produced by SPLParser#spl_prog.
    def enterSpl_prog(self, ctx:SPLParser.Spl_progContext):
        pass

    # Exit a parse tree produced by SPLParser#spl_prog.
    def exitSpl_prog(self, ctx:SPLParser.Spl_progContext):
        pass


    # Enter a parse tree produced by SPLParser#variables.
    def enterVariables(self, ctx:SPLParser.VariablesContext):
        pass

    # Exit a parse tree produced by SPLParser#variables.
    def exitVariables(self, ctx:SPLParser.VariablesContext):
        pass


    # Enter a parse tree produced by SPLParser#var.
    def enterVar(self, ctx:SPLParser.VarContext):
        pass

    # Exit a parse tree produced by SPLParser#var.
    def exitVar(self, ctx:SPLParser.VarContext):
        pass


    # Enter a parse tree produced by SPLParser#name.
    def enterName(self, ctx:SPLParser.NameContext):
        pass

    # Exit a parse tree produced by SPLParser#name.
    def exitName(self, ctx:SPLParser.NameContext):
        pass


    # Enter a parse tree produced by SPLParser#procdefs.
    def enterProcdefs(self, ctx:SPLParser.ProcdefsContext):
        pass

    # Exit a parse tree produced by SPLParser#procdefs.
    def exitProcdefs(self, ctx:SPLParser.ProcdefsContext):
        pass


    # Enter a parse tree produced by SPLParser#pdef.
    def enterPdef(self, ctx:SPLParser.PdefContext):
        pass

    # Exit a parse tree produced by SPLParser#pdef.
    def exitPdef(self, ctx:SPLParser.PdefContext):
        pass


    # Enter a parse tree produced by SPLParser#funcdefs.
    def enterFuncdefs(self, ctx:SPLParser.FuncdefsContext):
        pass

    # Exit a parse tree produced by SPLParser#funcdefs.
    def exitFuncdefs(self, ctx:SPLParser.FuncdefsContext):
        pass


    # Enter a parse tree produced by SPLParser#fdef.
    def enterFdef(self, ctx:SPLParser.FdefContext):
        pass

    # Exit a parse tree produced by SPLParser#fdef.
    def exitFdef(self, ctx:SPLParser.FdefContext):
        pass


    # Enter a parse tree produced by SPLParser#body.
    def enterBody(self, ctx:SPLParser.BodyContext):
        pass

    # Exit a parse tree produced by SPLParser#body.
    def exitBody(self, ctx:SPLParser.BodyContext):
        pass


    # Enter a parse tree produced by SPLParser#param.
    def enterParam(self, ctx:SPLParser.ParamContext):
        pass

    # Exit a parse tree produced by SPLParser#param.
    def exitParam(self, ctx:SPLParser.ParamContext):
        pass


    # Enter a parse tree produced by SPLParser#maxthree.
    def enterMaxthree(self, ctx:SPLParser.MaxthreeContext):
        pass

    # Exit a parse tree produced by SPLParser#maxthree.
    def exitMaxthree(self, ctx:SPLParser.MaxthreeContext):
        pass


    # Enter a parse tree produced by SPLParser#mainprog.
    def enterMainprog(self, ctx:SPLParser.MainprogContext):
        pass

    # Exit a parse tree produced by SPLParser#mainprog.
    def exitMainprog(self, ctx:SPLParser.MainprogContext):
        pass


    # Enter a parse tree produced by SPLParser#atom.
    def enterAtom(self, ctx:SPLParser.AtomContext):
        pass

    # Exit a parse tree produced by SPLParser#atom.
    def exitAtom(self, ctx:SPLParser.AtomContext):
        pass


    # Enter a parse tree produced by SPLParser#algo.
    def enterAlgo(self, ctx:SPLParser.AlgoContext):
        pass

    # Exit a parse tree produced by SPLParser#algo.
    def exitAlgo(self, ctx:SPLParser.AlgoContext):
        pass


    # Enter a parse tree produced by SPLParser#HaltInstr.
    def enterHaltInstr(self, ctx:SPLParser.HaltInstrContext):
        pass

    # Exit a parse tree produced by SPLParser#HaltInstr.
    def exitHaltInstr(self, ctx:SPLParser.HaltInstrContext):
        pass


    # Enter a parse tree produced by SPLParser#PrintInstr.
    def enterPrintInstr(self, ctx:SPLParser.PrintInstrContext):
        pass

    # Exit a parse tree produced by SPLParser#PrintInstr.
    def exitPrintInstr(self, ctx:SPLParser.PrintInstrContext):
        pass


    # Enter a parse tree produced by SPLParser#CallInstr.
    def enterCallInstr(self, ctx:SPLParser.CallInstrContext):
        pass

    # Exit a parse tree produced by SPLParser#CallInstr.
    def exitCallInstr(self, ctx:SPLParser.CallInstrContext):
        pass


    # Enter a parse tree produced by SPLParser#AssignInstr.
    def enterAssignInstr(self, ctx:SPLParser.AssignInstrContext):
        pass

    # Exit a parse tree produced by SPLParser#AssignInstr.
    def exitAssignInstr(self, ctx:SPLParser.AssignInstrContext):
        pass


    # Enter a parse tree produced by SPLParser#LoopInstr.
    def enterLoopInstr(self, ctx:SPLParser.LoopInstrContext):
        pass

    # Exit a parse tree produced by SPLParser#LoopInstr.
    def exitLoopInstr(self, ctx:SPLParser.LoopInstrContext):
        pass


    # Enter a parse tree produced by SPLParser#BranchInstr.
    def enterBranchInstr(self, ctx:SPLParser.BranchInstrContext):
        pass

    # Exit a parse tree produced by SPLParser#BranchInstr.
    def exitBranchInstr(self, ctx:SPLParser.BranchInstrContext):
        pass


    # Enter a parse tree produced by SPLParser#FunctionCallAssign.
    def enterFunctionCallAssign(self, ctx:SPLParser.FunctionCallAssignContext):
        pass

    # Exit a parse tree produced by SPLParser#FunctionCallAssign.
    def exitFunctionCallAssign(self, ctx:SPLParser.FunctionCallAssignContext):
        pass


    # Enter a parse tree produced by SPLParser#TermAssign.
    def enterTermAssign(self, ctx:SPLParser.TermAssignContext):
        pass

    # Exit a parse tree produced by SPLParser#TermAssign.
    def exitTermAssign(self, ctx:SPLParser.TermAssignContext):
        pass


    # Enter a parse tree produced by SPLParser#WhileLoop.
    def enterWhileLoop(self, ctx:SPLParser.WhileLoopContext):
        pass

    # Exit a parse tree produced by SPLParser#WhileLoop.
    def exitWhileLoop(self, ctx:SPLParser.WhileLoopContext):
        pass


    # Enter a parse tree produced by SPLParser#DoUntilLoop.
    def enterDoUntilLoop(self, ctx:SPLParser.DoUntilLoopContext):
        pass

    # Exit a parse tree produced by SPLParser#DoUntilLoop.
    def exitDoUntilLoop(self, ctx:SPLParser.DoUntilLoopContext):
        pass


    # Enter a parse tree produced by SPLParser#IfBranch.
    def enterIfBranch(self, ctx:SPLParser.IfBranchContext):
        pass

    # Exit a parse tree produced by SPLParser#IfBranch.
    def exitIfBranch(self, ctx:SPLParser.IfBranchContext):
        pass


    # Enter a parse tree produced by SPLParser#IfElseBranch.
    def enterIfElseBranch(self, ctx:SPLParser.IfElseBranchContext):
        pass

    # Exit a parse tree produced by SPLParser#IfElseBranch.
    def exitIfElseBranch(self, ctx:SPLParser.IfElseBranchContext):
        pass


    # Enter a parse tree produced by SPLParser#output.
    def enterOutput(self, ctx:SPLParser.OutputContext):
        pass

    # Exit a parse tree produced by SPLParser#output.
    def exitOutput(self, ctx:SPLParser.OutputContext):
        pass


    # Enter a parse tree produced by SPLParser#input.
    def enterInput(self, ctx:SPLParser.InputContext):
        pass

    # Exit a parse tree produced by SPLParser#input.
    def exitInput(self, ctx:SPLParser.InputContext):
        pass


    # Enter a parse tree produced by SPLParser#AtomTerm.
    def enterAtomTerm(self, ctx:SPLParser.AtomTermContext):
        pass

    # Exit a parse tree produced by SPLParser#AtomTerm.
    def exitAtomTerm(self, ctx:SPLParser.AtomTermContext):
        pass


    # Enter a parse tree produced by SPLParser#UnopTerm.
    def enterUnopTerm(self, ctx:SPLParser.UnopTermContext):
        pass

    # Exit a parse tree produced by SPLParser#UnopTerm.
    def exitUnopTerm(self, ctx:SPLParser.UnopTermContext):
        pass


    # Enter a parse tree produced by SPLParser#BinopTerm.
    def enterBinopTerm(self, ctx:SPLParser.BinopTermContext):
        pass

    # Exit a parse tree produced by SPLParser#BinopTerm.
    def exitBinopTerm(self, ctx:SPLParser.BinopTermContext):
        pass


    # Enter a parse tree produced by SPLParser#unop.
    def enterUnop(self, ctx:SPLParser.UnopContext):
        pass

    # Exit a parse tree produced by SPLParser#unop.
    def exitUnop(self, ctx:SPLParser.UnopContext):
        pass


    # Enter a parse tree produced by SPLParser#binop.
    def enterBinop(self, ctx:SPLParser.BinopContext):
        pass

    # Exit a parse tree produced by SPLParser#binop.
    def exitBinop(self, ctx:SPLParser.BinopContext):
        pass



del SPLParser