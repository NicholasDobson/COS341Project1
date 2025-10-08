grammar SPL;

// ============================================================================
// PARSER RULES
// ============================================================================

// Main program structure
spl_prog
    : 'glob' '{' variables '}' 
      'proc' '{' procdefs '}' 
      'func' '{' funcdefs '}' 
      'main' '{' mainprog '}'
    ;

// Variables (nullable)
variables
    : /* empty */
    | var variables
    ;

var
    : USER_DEFINED_NAME
    ;

name
    : USER_DEFINED_NAME
    ;

// Procedure definitions (nullable)
procdefs
    : /* empty */
    | pdef procdefs
    ;

pdef
    : name '(' param ')' '{' body '}'
    ;

// Function definitions (nullable)
funcdefs
    : fdef funcdefs
    | /* empty */
    ;

fdef
    : name '(' param ')' '{' body ';' 'return' atom '}'
    ;

// Body with local variables
body
    : 'local' '{' maxthree '}' algo
    ;

// Parameters (max 3)
param
    : maxthree
    ;

maxthree
    : /* empty */
    | var
    | var var
    | var var var
    ;

// Main program
mainprog
    : 'var' '{' variables '}' algo
    ;

// Atoms (variables or numbers)
atom
    : var
    | NUMBER
    ;

// Algorithm (sequence of instructions)
algo
    : instr
    | instr ';' algo
    ;

// Instructions
instr
    : 'halt'                                    # HaltInstr
    | 'print' output                            # PrintInstr
    | name '(' input ')'                        # CallInstr
    | assign                                    # AssignInstr
    | loop                                      # LoopInstr
    | branch                                    # BranchInstr
    ;

// Assignments
assign
    : var '=' name '(' input ')'                # FunctionCallAssign
    | var '=' term                              # TermAssign
    ;

// Loops
loop
    : 'while' term '{' algo '}'                 # WhileLoop
    | 'do' '{' algo '}' 'until' term            # DoUntilLoop
    ;

// Branches
branch
    : 'if' term '{' algo '}'                    # IfBranch
    | 'if' term '{' algo '}' 'else' '{' algo '}'  # IfElseBranch
    ;

// Output
output
    : atom
    | STRING
    ;

// Input (max 3 arguments, nullable)
input
    : /* empty */
    | atom
    | atom atom
    | atom atom atom
    ;

// Terms (expressions)
term
    : atom                                      # AtomTerm
    | '(' unop term ')'                         # UnopTerm
    | '(' term binop term ')'                   # BinopTerm
    ;

// Unary operators
unop
    : 'neg'
    | 'not'
    ;

// Binary operators
binop
    : 'eq'
    | '>'
    | 'or'
    | 'and'
    | 'plus'
    | 'minus'
    | 'mult'
    | 'div'
    ;

// ============================================================================
// LEXER RULES
// ============================================================================

// User-defined names: [a-z][a-z]*[0-9]*
USER_DEFINED_NAME
    : [a-z]+ [0-9]*
    ;

// Numbers: 0 | [1-9][0-9]*
NUMBER
    : '0'
    | [1-9] [0-9]*
    ;

// Strings: max 15 characters between quotes
STRING
    : '"' ~["\r\n]{0,15} '"'
    ;

// Whitespace (skip)
WS
    : [ \t\r\n]+ -> skip
    ;

// Comments (skip)
COMMENT
    : '//' ~[\r\n]* -> skip
    ;