"""
SPL Compiler - Complete Implementation
Phases: Lexing -> Parsing -> Scope Analysis -> Type Checking -> Code Generation

Usage:
    python compiler.py input.spl output.txt [--use-antlr]
    
Requirements:
    pip install antlr4-python3-runtime
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
import sys
import os

# ============================================================================
# ENUMS AND DATA STRUCTURES
# ============================================================================

class ScopeType(Enum):
    EVERYWHERE = "everywhere"
    GLOBAL = "global"
    PROCEDURE = "procedure"
    FUNCTION = "function"
    MAIN = "main"
    LOCAL = "local"

class VarType(Enum):
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    COMPARISON = "comparison"
    TYPELESS = "typeless"

@dataclass
class SymbolInfo:
    name: str
    node_id: int
    scope: ScopeType
    var_type: VarType
    parent_scope_id: Optional[int] = None
    is_parameter: bool = False
    is_local: bool = False
    is_global: bool = False
    is_main_var: bool = False
    procedure_name: Optional[str] = None  # If in procedure scope
    function_name: Optional[str] = None   # If in function scope
    internal_name: str = ""  # For code generation
    
@dataclass
class FunctionInfo:
    name: str
    params: List[str]
    body_node: Any
    is_procedure: bool = True

# ============================================================================
# SYMBOL TABLE
# ============================================================================

class SymbolTable:
    def __init__(self):
        self.symbols: Dict[int, SymbolInfo] = {}
        self.var_lookup: Dict[str, List[SymbolInfo]] = {}  # name -> list of symbols
        self.functions: Dict[str, FunctionInfo] = {}
        self.procedures: Dict[str, FunctionInfo] = {}
        self.global_vars: Set[str] = set()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.node_counter = 0
        self.temp_counter = 0
        self.label_counter = 0
        
        # Scope stack for proper scope management
        self.scope_stack: List[Dict[str, Any]] = []
        self.current_scope_type: Optional[ScopeType] = None
        
    def get_node_id(self) -> int:
        self.node_counter += 1
        return self.node_counter
        
    def new_temp(self) -> str:
        self.temp_counter += 1
        return f"t{self.temp_counter}"
        
    def new_label(self) -> str:
        self.label_counter += 1
        return f"L{self.label_counter}"
    
    # ========================================================================
    # SCOPE MANAGEMENT - Scope Stack Operations
    # ========================================================================
    
    def push_scope(self, scope_type: ScopeType, name: str = "", context: Dict[str, Any] = None):
        scope_info = {
            'type': scope_type,
            'name': name,
            'symbols': [],  # List of node_ids in this scope
            'parent': self.scope_stack[-1] if self.scope_stack else None,
            'context': context or {}
        }
        self.scope_stack.append(scope_info)
        self.current_scope_type = scope_type
    
    def pop_scope(self) -> Optional[Dict[str, Any]]:
        if not self.scope_stack:
            return None
        popped = self.scope_stack.pop()
        self.current_scope_type = self.scope_stack[-1]['type'] if self.scope_stack else None
        return popped
    
    def current_scope(self) -> Optional[Dict[str, Any]]:
        return self.scope_stack[-1] if self.scope_stack else None
    
    def get_current_scope_type(self) -> Optional[ScopeType]:
        return self.current_scope_type
    
    def scope_depth(self) -> int:
        return len(self.scope_stack)
    
    def get_parent_scope(self) -> Optional[Dict[str, Any]]:
        if len(self.scope_stack) >= 2:
            return self.scope_stack[-2]
        return None
    
    # ========================================================================
    # CRUD OPERATIONS
    # ========================================================================
    
    def add_error(self, msg: str):
        self.errors.append(f"ERROR: {msg}")
    
    def add_type_error(self, msg: str, line: int = 0):
        if line:
            self.errors.append(f"ERROR (Line {line}): TYPE-ERROR: {msg}")
        else:
            self.errors.append(f"ERROR: TYPE-ERROR: {msg}")
    
    def add_name_error(self, msg: str, line: int = 0):
        if line:
            self.errors.append(f"ERROR (Line {line}): NAME-RULE-VIOLATION: {msg}")
        else:
            self.errors.append(f"ERROR: NAME-RULE-VIOLATION: {msg}")
        
    def add_warning(self, msg: str):
        self.warnings.append(f"WARNING: {msg}")
    
    # CREATE
    def add_symbol(self, symbol: SymbolInfo) -> bool:
        if symbol.node_id in self.symbols:
            self.add_warning(f"Attempted to add duplicate node_id {symbol.node_id}")
            return False
        
        self.symbols[symbol.node_id] = symbol
        
        if symbol.name not in self.var_lookup:
            self.var_lookup[symbol.name] = []
        self.var_lookup[symbol.name].append(symbol)
        
        if self.scope_stack:
            self.scope_stack[-1]['symbols'].append(symbol.node_id)
        
        return True
    
    # READ
    def get_symbol(self, node_id: int) -> Optional[SymbolInfo]:
        return self.symbols.get(node_id)
    
    def lookup_var(self, name: str, scope_context: ScopeType = None) -> Optional[SymbolInfo]:
        if name not in self.var_lookup:
            return None
        
        if scope_context is None:
            scope_context = self.current_scope_type
        
        if scope_context is None:
            return self.var_lookup[name][-1] if self.var_lookup[name] else None
        
        for sym in reversed(self.var_lookup[name]):
            if scope_context == ScopeType.LOCAL:
                if sym.is_local or sym.is_parameter or sym.is_global:
                    return sym
            elif scope_context == ScopeType.MAIN:
                if sym.is_main_var or sym.is_global:
                    return sym
            elif scope_context == ScopeType.GLOBAL:
                if sym.is_global:
                    return sym
            elif scope_context in (ScopeType.PROCEDURE, ScopeType.FUNCTION):
                if sym.is_local or sym.is_parameter or sym.is_global:
                    return sym
        
        return None
    
    def get_symbol_by_name(self, name: str, scope: ScopeType = None) -> Optional[SymbolInfo]:
        if name not in self.var_lookup:
            return None
        symbols = self.var_lookup[name]
        if scope:
            symbols = [s for s in symbols if s.scope == scope]
        return symbols[0] if symbols else None
    
    def get_all_symbols_in_scope(self, scope: ScopeType) -> List[SymbolInfo]:
        return [s for s in self.symbols.values() if s.scope == scope]
    
    # UPDATE
    def update_symbol(self, node_id: int, **kwargs) -> bool:
        if node_id not in self.symbols:
            return False
        
        symbol = self.symbols[node_id]
        for field, value in kwargs.items():
            if hasattr(symbol, field):
                setattr(symbol, field, value)
            else:
                self.add_warning(f"Unknown field '{field}' in update_symbol")
        return True
    
    # DELETE
    def delete_symbol(self, node_id: int) -> bool:
        if node_id not in self.symbols:
            return False
        
        symbol = self.symbols[node_id]
        
        if symbol.name in self.var_lookup:
            self.var_lookup[symbol.name] = [
                s for s in self.var_lookup[symbol.name] 
                if s.node_id != node_id
            ]
            if not self.var_lookup[symbol.name]:
                del self.var_lookup[symbol.name]
        
        for scope in self.scope_stack:
            if node_id in scope['symbols']:
                scope['symbols'].remove(node_id)
        
        del self.symbols[node_id]
        return True
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def clear(self):
        self.symbols.clear()
        self.var_lookup.clear()
        self.functions.clear()
        self.procedures.clear()
        self.global_vars.clear()
        self.errors.clear()
        self.warnings.clear()
        self.scope_stack.clear()
        self.current_scope_type = None
        
    def has_errors(self) -> bool:
        return len(self.errors) > 0
        
    def print_report(self):
        if self.warnings:
            print("\n=== WARNINGS ===")
            for w in self.warnings:
                print(w)
        if self.errors:
            print("\n=== ERRORS ===")
            for e in self.errors:
                print(e)
        else:
            print("\n=== SUCCESS: No errors found ===")

# ============================================================================
# AST NODE DEFINITIONS
# ============================================================================

@dataclass
class ASTNode:
    node_id: int = 0
    line: int = 0
    
@dataclass
class ProgramNode(ASTNode):
    variables: List[str] = field(default_factory=list)
    procedures: List['ProcDefNode'] = field(default_factory=list)
    functions: List['FuncDefNode'] = field(default_factory=list)
    main: Optional['MainProgNode'] = None

@dataclass
class ProcDefNode(ASTNode):
    name: str = ""
    params: List[str] = field(default_factory=list)
    local_vars: List[str] = field(default_factory=list)
    body: Optional['AlgoNode'] = None

@dataclass
class FuncDefNode(ASTNode):
    name: str = ""
    params: List[str] = field(default_factory=list)
    local_vars: List[str] = field(default_factory=list)
    body: Optional['AlgoNode'] = None
    return_atom: Optional['AtomNode'] = None

@dataclass
class MainProgNode(ASTNode):
    variables: List[str] = field(default_factory=list)
    body: Optional['AlgoNode'] = None

@dataclass
class AlgoNode(ASTNode):
    instructions: List['InstrNode'] = field(default_factory=list)

@dataclass
class InstrNode(ASTNode):
    pass

@dataclass
class HaltNode(InstrNode):
    pass

@dataclass
class PrintNode(InstrNode):
    output: Any = None
    is_string: bool = False

@dataclass
class CallNode(InstrNode):
    name: str = ""
    args: List['AtomNode'] = field(default_factory=list)

@dataclass
class AssignNode(InstrNode):
    var: str = ""
    expr: Any = None  # TermNode or CallNode
    is_func_call: bool = False

@dataclass
class LoopNode(InstrNode):
    condition: Optional['TermNode'] = None
    body: Optional['AlgoNode'] = None
    is_while: bool = True

@dataclass
class BranchNode(InstrNode):
    condition: Optional['TermNode'] = None
    then_branch: Optional['AlgoNode'] = None
    else_branch: Optional['AlgoNode'] = None

@dataclass
class AtomNode(ASTNode):
    value: Any = None
    is_var: bool = True

@dataclass
class TermNode(ASTNode):
    pass

@dataclass
class AtomTermNode(TermNode):
    atom: Optional[AtomNode] = None

@dataclass
class UnopTermNode(TermNode):
    op: str = ""
    term: Optional[TermNode] = None

@dataclass
class BinopTermNode(TermNode):
    op: str = ""
    left: Optional[TermNode] = None
    right: Optional[TermNode] = None

# ============================================================================
# LEXER
# ============================================================================

class Token:
    def __init__(self, type_: str, value: str, line: int = 0):
        self.type = type_
        self.value = value
        self.line = line
        
    def __repr__(self):
        return f"Token({self.type}, '{self.value}', line {self.line})"

class Lexer:
    KEYWORDS = {
        'glob', 'proc', 'func', 'main', 'var', 'local', 'return',
        'halt', 'print', 'if', 'else', 'while', 'do', 'until',
        'neg', 'not', 'eq', 'or', 'and', 'plus', 'minus', 'mult', 'div'
    }
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.tokens: List[Token] = []
        
    def tokenize(self) -> List[Token]:
        while self.pos < len(self.text):
            self.skip_whitespace()
            if self.pos >= len(self.text):
                break
                
            # Comments
            if self.pos < len(self.text) - 1 and self.text[self.pos:self.pos+2] == '//':
                self.skip_line()
                continue
                
            # String literals
            if self.current() == '"':
                self.tokens.append(self.read_string())
                continue
                
            # Numbers
            if self.current().isdigit():
                self.tokens.append(self.read_number())
                continue
                
            # Identifiers and keywords - SPL Vocabulary Rules
            if self.current().isalpha() and self.current().islower():
                self.tokens.append(self.read_identifier())
                continue
            
            # Reject uppercase letters - not allowed in SPL vocabulary
            if self.current().isupper():
                raise ValueError(f"Vocabulary violation: Uppercase letter '{self.current()}' not allowed in SPL at line {self.line}")
                
            # Symbols
            c = self.current()
            if c in '(){}[];=><':
                self.tokens.append(Token('SYMBOL', c, self.line))
                self.pos += 1
                continue
                
            # Unknown character - this is a vocabulary violation in SPL
            raise ValueError(f"Vocabulary violation: Invalid character '{c}' at line {self.line}, position {self.pos}")
            
        self.tokens.append(Token('EOF', '', self.line))
        return self.tokens
        
    def current(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ''
        
    def peek(self, n=1) -> str:
        if self.pos >= len(self.text):
            return ''
        end_pos = min(self.pos + n, len(self.text))
        return self.text[self.pos:end_pos]
        
    def skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos] in ' \t\n\r':
            if self.text[self.pos] == '\n':
                self.line += 1
            self.pos += 1
            
    def skip_line(self):
        while self.pos < len(self.text) and self.text[self.pos] not in '\n\r':
            self.pos += 1
            
    def read_string(self) -> Token:
        start_line = self.line
        start = self.pos
        self.pos += 1  # skip opening "
        count = 0
        while self.pos < len(self.text) and self.text[self.pos] != '"' and count < 50:
            if self.text[self.pos] == '\n':
                self.line += 1
            self.pos += 1
            count += 1
        
        if count >= 50:
            raise ValueError(f"String too long (max 50 characters) at line {start_line}")
            
        if self.pos < len(self.text) and self.text[self.pos] == '"':
            self.pos += 1  # skip closing "
        else:
            raise ValueError(f"Unterminated string at line {start_line}")
            
        value = self.text[start:self.pos]
        return Token('STRING', value, start_line)
        
    def read_number(self) -> Token:
        start = self.pos
        start_line = self.line
        
        if self.text[self.pos] == '0':
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos].isdigit():
                raise ValueError(f"Invalid number format: leading zero not allowed except for '0' at line {start_line}")
        else:
            if not (self.text[self.pos].isdigit() and self.text[self.pos] != '0'):
                raise ValueError(f"Invalid number format at line {start_line}")
            self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
                
        return Token('NUMBER', self.text[start:self.pos], start_line)
        
    def read_identifier(self) -> Token:
        start = self.pos
        start_line = self.line
        
        if self.pos >= len(self.text) or not self.text[self.pos].islower():
            raise ValueError(f"Invalid identifier start at position {self.pos}")
        
        while self.pos < len(self.text) and self.text[self.pos].islower():
            self.pos += 1
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1
            
        value = self.text[start:self.pos]
        if len(value) == 0:
            raise ValueError(f"Empty identifier at position {start}")
        if value in self.KEYWORDS:
            return Token('KEYWORD', value, start_line)
        return Token('ID', value, start_line)

# ============================================================================
# PARSER
# ============================================================================

class Parser:
    def __init__(self, tokens: List[Token], symbol_table: SymbolTable):
        self.tokens = tokens
        self.pos = 0
        self.st = symbol_table
        
    def error(self, msg: str):
        tok = self.current()
        raise SyntaxError(f"Line {tok.line}: {msg}")
        
    def current(self) -> Token:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]
        
    def peek(self, offset=1) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]
        
    def consume(self, expected: str = None) -> Token:
        tok = self.current()
        if expected and tok.value != expected:
            self.error(f"Expected '{expected}', got '{tok.value}'")
        self.pos += 1
        return tok
        
    def match(self, value: str) -> bool:
        return self.current().value == value
        
    def match_type(self, type_: str) -> bool:
        return self.current().type == type_
        
    def parse(self) -> ProgramNode:
        try:
            return self.parse_program()
        except SyntaxError as e:
            self.st.add_error(str(e))
            return None
        
    def parse_program(self) -> ProgramNode:
        node = ProgramNode(node_id=self.st.get_node_id(), line=self.current().line)
        
        self.consume('glob')
        self.consume('{')
        node.variables = self.parse_variables()
        self.consume('}')
        
        self.consume('proc')
        self.consume('{')
        node.procedures = self.parse_procdefs()
        self.consume('}')
        
        self.consume('func')
        self.consume('{')
        node.functions = self.parse_funcdefs()
        self.consume('}')
        
        self.consume('main')
        self.consume('{')
        node.main = self.parse_mainprog()
        self.consume('}')
        
        return node
        
    def parse_variables(self) -> List[str]:
        vars = []
        while self.match_type('ID'):
            vars.append(self.consume().value)
        return vars
        
    def parse_procdefs(self) -> List[ProcDefNode]:
        procs = []
        while self.match_type('ID'):
            procs.append(self.parse_pdef())
        return procs
        
    def parse_pdef(self) -> ProcDefNode:
        node = ProcDefNode(node_id=self.st.get_node_id(), line=self.current().line)
        node.name = self.consume().value
        self.consume('(')
        node.params = self.parse_maxthree()
        self.consume(')')
        self.consume('{')
        node.local_vars, node.body = self.parse_body()
        self.consume('}')
        return node
        
    def parse_funcdefs(self) -> List[FuncDefNode]:
        funcs = []
        while self.match_type('ID'):
            funcs.append(self.parse_fdef())
        return funcs
        
    def parse_fdef(self) -> FuncDefNode:
        node = FuncDefNode(node_id=self.st.get_node_id(), line=self.current().line)
        node.name = self.consume().value
        self.consume('(')
        node.params = self.parse_maxthree()
        self.consume(')')
        self.consume('{')
        node.local_vars, node.body = self.parse_body()
        
        # Handle optional semicolon before return
        if self.match(';'):
            self.consume(';')
        
        self.consume('return')
        node.return_atom = self.parse_atom()
        self.consume('}')
        return node
        
    def parse_body(self):
        self.consume('local')
        self.consume('{')
        local_vars = self.parse_maxthree()
        self.consume('}')
        algo = self.parse_algo()
        return local_vars, algo
        
    def parse_maxthree(self) -> List[str]:
        vars = []
        for _ in range(3):
            if self.match_type('ID') and not self.match('{'):
                vars.append(self.consume().value)
            else:
                break
        return vars
        
    def parse_mainprog(self) -> MainProgNode:
        node = MainProgNode(node_id=self.st.get_node_id(), line=self.current().line)
        self.consume('var')
        self.consume('{')
        node.variables = self.parse_variables()
        self.consume('}')
        node.body = self.parse_algo()
        return node
        
    def parse_algo(self) -> AlgoNode:
        node = AlgoNode(node_id=self.st.get_node_id(), line=self.current().line)
        
        # Check if we have any instructions (algorithm might be empty)
        if not self.match('}') and not self.match('return') and not self.match('until'):
            node.instructions.append(self.parse_instr())
            
            while self.match(';'):
                self.consume(';')
                if not self.match('}') and not self.match('until') and not self.match('return'):
                    node.instructions.append(self.parse_instr())
                else:
                    break
        return node
        
    def parse_instr(self) -> InstrNode:
        if self.match('halt'):
            self.consume('halt')
            return HaltNode(node_id=self.st.get_node_id(), line=self.current().line)
            
        if self.match('print'):
            self.consume('print')
            node = PrintNode(node_id=self.st.get_node_id(), line=self.current().line)
            if self.match_type('STRING'):
                node.output = self.consume().value
                node.is_string = True
            else:
                node.output = self.parse_atom()
                node.is_string = False
            return node
            
        if self.match('if'):
            return self.parse_branch()
            
        if self.match('while') or self.match('do'):
            return self.parse_loop()
            
        # Assignment or procedure call
        if self.match_type('ID'):
            var_name = self.consume().value
            
            if self.match('='):
                self.consume('=')
                node = AssignNode(node_id=self.st.get_node_id(), line=self.current().line)
                node.var = var_name
                
                # Check for function call
                if self.match_type('ID'):
                    checkpoint = self.pos
                    func_name = self.consume().value
                    if self.match('('):
                        self.consume('(')
                        args = self.parse_input()
                        self.consume(')')
                        call = CallNode()
                        call.name = func_name
                        call.args = args
                        node.expr = call
                        node.is_func_call = True
                    else:
                        self.pos = checkpoint
                        node.expr = self.parse_term()
                else:
                    node.expr = self.parse_term()
                return node
                
            elif self.match('('):
                # Procedure call
                self.consume('(')
                node = CallNode(node_id=self.st.get_node_id(), line=self.current().line)
                node.name = var_name
                node.args = self.parse_input()
                self.consume(')')
                return node
                
        self.error(f"Unexpected token in instruction: {self.current()}")
        
    def parse_branch(self) -> BranchNode:
        node = BranchNode(node_id=self.st.get_node_id(), line=self.current().line)
        self.consume('if')
        node.condition = self.parse_term()
        self.consume('{')
        node.then_branch = self.parse_algo()
        self.consume('}')
        
        if self.match('else'):
            self.consume('else')
            self.consume('{')
            node.else_branch = self.parse_algo()
            self.consume('}')
            
        return node
        
    def parse_loop(self) -> LoopNode:
        node = LoopNode(node_id=self.st.get_node_id(), line=self.current().line)
        
        if self.match('while'):
            self.consume('while')
            node.is_while = True
            node.condition = self.parse_term()
            self.consume('{')
            node.body = self.parse_algo()
            self.consume('}')
        else:
            self.consume('do')
            node.is_while = False
            self.consume('{')
            node.body = self.parse_algo()
            self.consume('}')
            self.consume('until')
            node.condition = self.parse_term()
            
        return node
        
    def parse_input(self) -> List[AtomNode]:
        args = []
        for _ in range(3):
            if not self.match(')'):
                args.append(self.parse_atom())
            else:
                break
        return args
        
    def parse_atom(self) -> AtomNode:
        node = AtomNode(node_id=self.st.get_node_id(), line=self.current().line)
        tok = self.current()
        
        if tok.type == 'NUMBER':
            node.value = int(self.consume().value)
            node.is_var = False
        elif tok.type == 'ID':
            node.value = self.consume().value
            node.is_var = True
        else:
            self.error(f"Expected atom, got {tok}")
            
        return node
        
    def parse_term(self) -> TermNode:
        if self.match('('):
            self.consume('(')
            
            if self.match('neg') or self.match('not'):
                node = UnopTermNode(node_id=self.st.get_node_id(), line=self.current().line)
                node.op = self.consume().value
                node.term = self.parse_term()
                self.consume(')')
                return node
            
            if self.current().value in ['eq', '>', 'or', 'and', 'plus', 'minus', 'mult', 'div']:
                node = BinopTermNode(node_id=self.st.get_node_id(), line=self.current().line)
                node.op = self.consume().value
                node.left = self.parse_term()
                node.right = self.parse_term()
                self.consume(')')
                return node
            
            left_term = self.parse_term()
            if self.current().value in ['eq', '>', 'or', 'and', 'plus', 'minus', 'mult', 'div']:
                node = BinopTermNode(node_id=self.st.get_node_id(), line=self.current().line)
                node.left = left_term
                node.op = self.consume().value
                node.right = self.parse_term()
                self.consume(')')
                return node
            
            self.consume(')')
            return left_term
            
        node = AtomTermNode(node_id=self.st.get_node_id(), line=self.current().line)
        node.atom = self.parse_atom()
        return node

# ============================================================================
# SCOPE ANALYZER - NAME-SCOPE-RULES COMPLIANT
# ============================================================================

class ScopeAnalyzer:
    def __init__(self, ast: ProgramNode, symbol_table: SymbolTable):
        self.ast = ast
        self.st = symbol_table
        self.global_variables: Set[str] = set()
        self.procedure_names: Set[str] = set()
        self.function_names: Set[str] = set()
        
    def analyze(self):
        if not self.ast:
            return
        print("Starting NAME-SCOPE-RULES analysis...")
        self.collect_everywhere_scope_names()
        self.check_everywhere_scope_conflicts()
        self.analyze_global_scope()
        self.analyze_procedure_scope()
        self.analyze_function_scope()
        self.analyze_main_scope()
        print("NAME-SCOPE-RULES analysis completed.")
    
    def collect_everywhere_scope_names(self):
        for var in self.ast.variables:
            if var in self.global_variables:
                self.emit_name_rule_violation(f"double-declaration: Duplicate global variable declaration: '{var}'")
            else:
                self.global_variables.add(var)
                self.st.global_vars.add(var)
                symbol = SymbolInfo(
                    name=var,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.GLOBAL,
                    var_type=VarType.TYPELESS,
                    is_global=True
                )
                self.st.add_symbol(symbol)
        
        for proc in self.ast.procedures:
            if proc.name in self.procedure_names:
                self.emit_name_rule_violation(f"double-declaration: Duplicate procedure declaration: '{proc.name}'")
            else:
                self.procedure_names.add(proc.name)
                self.st.procedures[proc.name] = FunctionInfo(
                    proc.name, proc.params, proc, is_procedure=True
                )
        
        for func in self.ast.functions:
            if func.name in self.function_names:
                self.emit_name_rule_violation(f"double-declaration: Duplicate function declaration: '{func.name}'")
            else:
                self.function_names.add(func.name)
                self.st.functions[func.name] = FunctionInfo(
                    func.name, func.params, func, is_procedure=False
                )
    
    def check_everywhere_scope_conflicts(self):
        var_func_conflicts = self.global_variables & self.function_names
        for name in var_func_conflicts:
            self.emit_name_rule_violation(f"Variable name '{name}' conflicts with function name")
        var_proc_conflicts = self.global_variables & self.procedure_names
        for name in var_proc_conflicts:
            self.emit_name_rule_violation(f"Variable name '{name}' conflicts with procedure name")
        func_proc_conflicts = self.function_names & self.procedure_names
        for name in func_proc_conflicts:
            self.emit_name_rule_violation(f"Function name '{name}' conflicts with procedure name")
    
    def analyze_global_scope(self):
        pass
    
    def analyze_procedure_scope(self):
        for proc in self.ast.procedures:
            self.analyze_procedure_local_scope(proc)
    
    def analyze_function_scope(self):
        for func in self.ast.functions:
            self.analyze_function_local_scope(func)
    
    def analyze_main_scope(self):
        if not self.ast.main:
            return
        main_vars = set()
        for var in self.ast.main.variables:
            if var in main_vars:
                self.emit_name_rule_violation(f"double-declaration: Duplicate variable declaration in main: '{var}'")
            else:
                main_vars.add(var)
                symbol = SymbolInfo(
                    name=var,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.MAIN,
                    var_type=VarType.TYPELESS,
                    is_main_var=True
                )
                self.st.add_symbol(symbol)
        if self.ast.main.body:
            self.analyze_algo_variables(self.ast.main.body, ScopeType.MAIN, 
                                      params=[], local_vars=[], main_vars=list(main_vars))
    
    def analyze_procedure_local_scope(self, proc: ProcDefNode):
        param_set = set()
        for param in proc.params:
            if param in param_set:
                self.emit_name_rule_violation(f"double-declaration: Duplicate parameter in procedure '{proc.name}': '{param}'")
            else:
                param_set.add(param)
                symbol = SymbolInfo(
                    name=param,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.LOCAL,
                    var_type=VarType.TYPELESS,
                    is_parameter=True,
                    procedure_name=proc.name
                )
                self.st.add_symbol(symbol)
        
        local_set = set()
        for local_var in proc.local_vars:
            if local_var in local_set:
                self.emit_name_rule_violation(f"double-declaration: Duplicate local variable in procedure '{proc.name}': '{local_var}'")
            elif local_var in param_set:
                self.emit_name_rule_violation(f"shadowing: Local variable '{local_var}' shadows parameter in procedure '{proc.name}'")
            else:
                local_set.add(local_var)
                symbol = SymbolInfo(
                    name=local_var,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.LOCAL,
                    var_type=VarType.TYPELESS,
                    is_local=True,
                    procedure_name=proc.name
                )
                self.st.add_symbol(symbol)
        
        if proc.body:
            self.analyze_algo_variables(proc.body, ScopeType.LOCAL, 
                                      params=list(param_set), local_vars=list(local_set), 
                                      procedure_name=proc.name)
    
    def analyze_function_local_scope(self, func: FuncDefNode):
        param_set = set()
        for param in func.params:
            if param in param_set:
                self.emit_name_rule_violation(f"double-declaration: Duplicate parameter in function '{func.name}': '{param}'")
            else:
                param_set.add(param)
                symbol = SymbolInfo(
                    name=param,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.LOCAL,
                    var_type=VarType.TYPELESS,
                    is_parameter=True,
                    function_name=func.name
                )
                self.st.add_symbol(symbol)
        
        local_set = set()
        for local_var in func.local_vars:
            if local_var in local_set:
                self.emit_name_rule_violation(f"double-declaration: Duplicate local variable in function '{func.name}': '{local_var}'")
            elif local_var in param_set:
                self.emit_name_rule_violation(f"shadowing: Local variable '{local_var}' shadows parameter in function '{func.name}'")
            else:
                local_set.add(local_var)
                symbol = SymbolInfo(
                    name=local_var,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.LOCAL,
                    var_type=VarType.TYPELESS,
                    is_local=True,
                    function_name=func.name
                )
                self.st.add_symbol(symbol)
        
        if func.body:
            self.analyze_algo_variables(func.body, ScopeType.LOCAL, 
                                      params=list(param_set), local_vars=list(local_set), 
                                      function_name=func.name)
        
        if func.return_atom and func.return_atom.is_var:
            self.check_variable_declaration(func.return_atom.value, ScopeType.LOCAL, 
                                          params=list(param_set), local_vars=list(local_set),
                                          main_vars=[], function_name=func.name)
    
    def analyze_algo_variables(self, algo: AlgoNode, current_scope: ScopeType, 
                             params: List[str] = None, local_vars: List[str] = None,
                             main_vars: List[str] = None, procedure_name: str = None,
                             function_name: str = None):
        params = params or []
        local_vars = local_vars or []
        main_vars = main_vars or []
        
        for instr in algo.instructions:
            self.analyze_instruction_variables(instr, current_scope, params, local_vars, 
                                             main_vars, procedure_name, function_name)
    
    def analyze_instruction_variables(self, instr: InstrNode, current_scope: ScopeType,
                                    params: List[str], local_vars: List[str], 
                                    main_vars: List[str], procedure_name: str = None,
                                    function_name: str = None):
        if isinstance(instr, AssignNode):
            self.check_variable_declaration(instr.var, current_scope, params, local_vars, 
                                          main_vars, procedure_name, function_name)
            if isinstance(instr.expr, TermNode):
                self.analyze_term_variables(instr.expr, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
            elif instr.is_func_call and isinstance(instr.expr, CallNode):
                self.analyze_call_variables(instr.expr, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
        elif isinstance(instr, CallNode):
            self.analyze_call_variables(instr, current_scope, params, local_vars,
                                      main_vars, procedure_name, function_name)
        elif isinstance(instr, PrintNode):
            if not instr.is_string and isinstance(instr.output, AtomNode) and instr.output.is_var:
                self.check_variable_declaration(instr.output.value, current_scope, params, 
                                              local_vars, main_vars, procedure_name, function_name)
        elif isinstance(instr, BranchNode):
            if instr.condition:
                self.analyze_term_variables(instr.condition, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
            if instr.then_branch:
                self.analyze_algo_variables(instr.then_branch, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
            if instr.else_branch:
                self.analyze_algo_variables(instr.else_branch, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
        elif isinstance(instr, LoopNode):
            if instr.condition:
                self.analyze_term_variables(instr.condition, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
            if instr.body:
                self.analyze_algo_variables(instr.body, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
    
    def analyze_call_variables(self, call: CallNode, current_scope: ScopeType,
                             params: List[str], local_vars: List[str], main_vars: List[str],
                             procedure_name: str = None, function_name: str = None):
        if call.name not in self.procedure_names and call.name not in self.function_names:
            self.st.add_error(f"undeclared: Undeclared procedure or function: '{call.name}'")
        for arg in call.args:
            if arg.is_var:
                self.check_variable_declaration(arg.value, current_scope, params, local_vars,
                                              main_vars, procedure_name, function_name)
    
    def analyze_term_variables(self, term: TermNode, current_scope: ScopeType,
                             params: List[str], local_vars: List[str], main_vars: List[str],
                             procedure_name: str = None, function_name: str = None):
        if isinstance(term, AtomTermNode):
            if term.atom and term.atom.is_var:
                self.check_variable_declaration(term.atom.value, current_scope, params, 
                                              local_vars, main_vars, procedure_name, function_name)
        elif isinstance(term, UnopTermNode):
            if term.term:
                self.analyze_term_variables(term.term, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
        elif isinstance(term, BinopTermNode):
            if term.left:
                self.analyze_term_variables(term.left, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
            if term.right:
                self.analyze_term_variables(term.right, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
    
    def check_variable_declaration(self, var_name: str, current_scope: ScopeType,
                                 params: List[str], local_vars: List[str], main_vars: List[str],
                                 procedure_name: str = None, function_name: str = None):
        if current_scope == ScopeType.LOCAL:
            if procedure_name:
                if var_name in params:
                    self.update_symbol_table_for_var(var_name, ScopeType.LOCAL, is_parameter=True,
                                                   procedure_name=procedure_name)
                    return
                elif var_name in local_vars:
                    self.update_symbol_table_for_var(var_name, ScopeType.LOCAL, is_local=True,
                                                   procedure_name=procedure_name)
                    return
                elif var_name in self.global_variables:
                    self.update_symbol_table_for_var(var_name, ScopeType.GLOBAL, is_global=True)
                    return
                else:
                    self.emit_undeclared_variable(var_name, f"procedure '{procedure_name}'")
                    
            elif function_name:
                if var_name in params:
                    self.update_symbol_table_for_var(var_name, ScopeType.LOCAL, is_parameter=True,
                                                   function_name=function_name)
                    return
                elif var_name in local_vars:
                    self.update_symbol_table_for_var(var_name, ScopeType.LOCAL, is_local=True,
                                                   function_name=function_name)
                    return
                elif var_name in self.global_variables:
                    self.update_symbol_table_for_var(var_name, ScopeType.GLOBAL, is_global=True)
                    return
                else:
                    self.emit_undeclared_variable(var_name, f"function '{function_name}'")
                    
        elif current_scope == ScopeType.MAIN:
            if var_name in main_vars:
                self.update_symbol_table_for_var(var_name, ScopeType.MAIN, is_main_var=True)
                return
            elif var_name in self.global_variables:
                self.update_symbol_table_for_var(var_name, ScopeType.GLOBAL, is_global=True)
                return
            else:
                self.emit_undeclared_variable(var_name, "main")
    
    def update_symbol_table_for_var(self, var_name: str, scope: ScopeType, 
                                   is_parameter: bool = False, is_local: bool = False,
                                   is_global: bool = False, is_main_var: bool = False,
                                   procedure_name: str = None, function_name: str = None):
        symbol = SymbolInfo(
            name=var_name,
            node_id=self.st.get_node_id(),
            scope=scope,
            var_type=VarType.TYPELESS,
            is_parameter=is_parameter,
            is_local=is_local,
            is_global=is_global,
            is_main_var=is_main_var,
            procedure_name=procedure_name,
            function_name=function_name
        )
        self.st.add_symbol(symbol)
    
    def emit_name_rule_violation(self, message: str):
        self.st.add_error(f"NAME-RULE-VIOLATION: {message}")
    
    def emit_undeclared_variable(self, var_name: str, context: str):
        self.st.add_error(f"undeclared: UNDECLARED-VARIABLE: '{var_name}' in {context}")
    
    def print_symbol_table_report(self):
        print("\n=== SYMBOL TABLE REPORT ===")
        print(f"Global Variables: {self.global_variables}")
        print(f"Procedure Names: {self.procedure_names}")
        print(f"Function Names: {self.function_names}")
        print("\nSymbol Table Entries:")
        for node_id, symbol in self.st.symbols.items():
            print(f"  Node {node_id}: {symbol.name} [{symbol.scope.value}] "
                  f"{'(param)' if symbol.is_parameter else ''}"
                  f"{'(local)' if symbol.is_local else ''}"
                  f"{'(global)' if symbol.is_global else ''}"
                  f"{'(main)' if symbol.is_main_var else ''}"
                  f"{' in ' + symbol.procedure_name if symbol.procedure_name else ''}"
                  f"{' in ' + symbol.function_name if symbol.function_name else ''}")
        print("=== END SYMBOL TABLE REPORT ===\n")
        
    def analyze_procedure(self, proc: ProcDefNode):
        if len(proc.params) != len(set(proc.params)):
            self.st.add_error(f"Duplicate parameters in procedure {proc.name}")
        if len(proc.local_vars) != len(set(proc.local_vars)):
            self.st.add_error(f"Duplicate local variables in procedure {proc.name}")
        param_set = set(proc.params)
        for local_var in proc.local_vars:
            if local_var in param_set:
                self.st.add_error(f"shadowing: Local variable '{local_var}' shadows parameter in procedure {proc.name}")
        if proc.body:
            self.analyze_algo(proc.body, proc.params, proc.local_vars, ScopeType.LOCAL)
        
    def analyze_function(self, func: FuncDefNode):
        if len(func.params) != len(set(func.params)):
            self.st.add_error(f"Duplicate parameters in function {func.name}")
        if len(func.local_vars) != len(set(func.local_vars)):
            self.st.add_error(f"Duplicate local variables in function {func.name}")
        param_set = set(func.params)
        for local_var in func.local_vars:
            if local_var in param_set:
                self.st.add_error(f"shadowing: Local variable '{local_var}' shadows parameter in function {func.name}")
        if func.body:
            self.analyze_algo(func.body, func.params, func.local_vars, ScopeType.LOCAL)
        if func.return_atom:
            self.check_variable_usage(func.return_atom, func.params, func.local_vars, ScopeType.LOCAL)
    
    def analyze_main(self, main: MainProgNode):
        if len(main.variables) != len(set(main.variables)):
            self.st.add_error("Duplicate variables in main program")
        main_vars = set(main.variables)
        conflicts = main_vars & self.st.global_vars
        if conflicts:
            self.st.add_warning(f"Main variables shadow global variables: {conflicts}")
        if main.body:
            self.analyze_algo(main.body, [], main.variables, ScopeType.MAIN)
    
    def analyze_algo(self, algo: AlgoNode, params: List[str], local_vars: List[str], scope: ScopeType):
        for instr in algo.instructions:
            self.analyze_instruction(instr, params, local_vars, scope)
    
    def analyze_instruction(self, instr: InstrNode, params: List[str], local_vars: List[str], scope: ScopeType):
        if isinstance(instr, AssignNode):
            if not self.is_variable_in_scope(instr.var, params, local_vars, scope):
                self.st.add_error(f"Variable '{instr.var}' not in scope for assignment")
            if instr.is_func_call and isinstance(instr.expr, CallNode):
                self.check_function_call(instr.expr, params, local_vars, scope)
            elif isinstance(instr.expr, TermNode):
                self.check_term(instr.expr, params, local_vars, scope)
        elif isinstance(instr, CallNode):
            self.check_procedure_call(instr, params, local_vars, scope)
        elif isinstance(instr, PrintNode):
            if not instr.is_string and isinstance(instr.output, AtomNode):
                self.check_variable_usage(instr.output, params, local_vars, scope)
        elif isinstance(instr, BranchNode):
            if instr.condition:
                self.check_term(instr.condition, params, local_vars, scope)
            if instr.then_branch:
                self.analyze_algo(instr.then_branch, params, local_vars, scope)
            if instr.else_branch:
                self.analyze_algo(instr.else_branch, params, local_vars, scope)
        elif isinstance(instr, LoopNode):
            if instr.condition:
                self.check_term(instr.condition, params, local_vars, scope)
            if instr.body:
                self.analyze_algo(instr.body, params, local_vars, scope)
    
    def check_function_call(self, call: CallNode, params: List[str], local_vars: List[str], scope: ScopeType):
        if call.name not in self.st.functions:
            self.st.add_error(f"Unknown function: {call.name}")
        else:
            func_info = self.st.functions[call.name]
            if len(call.args) != len(func_info.params):
                self.st.add_error(f"Function {call.name} expects {len(func_info.params)} arguments, got {len(call.args)}")
            for arg in call.args:
                self.check_variable_usage(arg, params, local_vars, scope)
    
    def check_procedure_call(self, call: CallNode, params: List[str], local_vars: List[str], scope: ScopeType):
        if call.name not in self.st.procedures:
            self.st.add_error(f"Unknown procedure: {call.name}")
        else:
            proc_info = self.st.procedures[call.name]
            if len(call.args) != len(proc_info.params):
                self.st.add_error(f"Procedure {call.name} expects {len(proc_info.params)} arguments, got {len(call.args)}")
            for arg in call.args:
                self.check_variable_usage(arg, params, local_vars, scope)
    
    def check_term(self, term: TermNode, params: List[str], local_vars: List[str], scope: ScopeType):
        if isinstance(term, AtomTermNode):
            if term.atom:
                self.check_variable_usage(term.atom, params, local_vars, scope)
        elif isinstance(term, UnopTermNode):
            if term.term:
                self.check_term(term.term, params, local_vars, scope)
        elif isinstance(term, BinopTermNode):
            if term.left:
                self.check_term(term.left, params, local_vars, scope)
            if term.right:
                self.check_term(term.right, params, local_vars, scope)
    
    def check_variable_usage(self, atom: AtomNode, params: List[str], local_vars: List[str], scope: ScopeType):
        if atom.is_var and not self.is_variable_in_scope(atom.value, params, local_vars, scope):
            self.st.add_error(f"Variable '{atom.value}' not in scope")
    
    def is_variable_in_scope(self, var_name: str, params: List[str], local_vars: List[str], scope: ScopeType) -> bool:
        if var_name in params or var_name in local_vars:
            return True
        if var_name in self.st.global_vars:
            return True
        return False

# ============================================================================
# TYPE ANALYZER
# ============================================================================

class TypeAnalyzer:
    """
    COS341 Type Analyzer - Implements formal type analysis rules for SPL
    """
    
    def __init__(self, ast: ProgramNode, symbol_table: SymbolTable):
        self.ast = ast
        self.st = symbol_table
        
    def analyze(self) -> bool:
        print("Phase 4: Type Analysis (COS341 Formal Rules)...")
        
        if not self.ast:
            self.st.add_error("AST is None - cannot perform type analysis")
            return False
            
        variables_correct = self.check_variables(self.ast.variables)
        procdefs_correct = self.check_procdefs(self.ast.procedures)
        funcdefs_correct = self.check_funcdefs(self.ast.functions)
        mainprog_correct = self.check_mainprog(self.ast.main)
        
        is_correctly_typed = (variables_correct and procdefs_correct and 
                            funcdefs_correct and mainprog_correct)
        
        if is_correctly_typed:
            print("Type analysis passed - program is correctly typed")
        else:
            print("Type analysis failed - program has type errors \n")
        return is_correctly_typed
    
    def check_variables(self, variables: List[str]) -> bool:
        return True
    
    def check_procdefs(self, procedures: List[ProcDefNode]) -> bool:
        for proc in procedures:
            if not self.check_pdef(proc):
                return False
        return True
    
    def check_pdef(self, proc: ProcDefNode) -> bool:
        param_correct = self.check_param(proc.params)
        body_correct = self.check_body(proc.local_vars, proc.body)
        if not (param_correct and body_correct):
            self.st.add_error(f"Procedure '{proc.name}' is not correctly typed")
            return False
        return True
    
    def check_funcdefs(self, functions: List[FuncDefNode]) -> bool:
        for func in functions:
            if not self.check_fdef(func):
                return False
        return True
    
    def check_fdef(self, func: FuncDefNode) -> bool:
        param_correct = self.check_param(func.params)
        body_correct = self.check_body(func.local_vars, func.body)
        atom_correct = False
        if func.return_atom:
            atom_type = self.get_atom_type(func.return_atom)
            atom_correct = (atom_type == VarType.NUMERIC)
            if not atom_correct:
                self.st.add_error(f"Function '{func.name}' return value is not of type 'numeric'")
        else:
            self.st.add_error(f"Function '{func.name}' missing return statement")
        
        if not (param_correct and body_correct and atom_correct):
            self.st.add_error(f"Function '{func.name}' is not correctly typed")
            return False
        return True
    
    def check_mainprog(self, main: MainProgNode) -> bool:
        if not main:
            self.st.add_error("Main program is missing")
            return False
        variables_correct = self.check_variables(main.variables)
        algo_correct = self.check_algo(main.body)
        if not (variables_correct and algo_correct):
            self.st.add_error("Main program is not correctly typed")
            return False
        return True
    
    def check_body(self, local_vars: List[str], body: AlgoNode) -> bool:
        maxthree_correct = self.check_maxthree(local_vars)
        algo_correct = self.check_algo(body)
        return maxthree_correct and algo_correct
    
    def check_param(self, params: List[str]) -> bool:
        return self.check_maxthree(params)
    
    def check_maxthree(self, vars_list: List[str]) -> bool:
        if len(vars_list) > 3:
            self.st.add_error(f"Too many variables in MAXTHREE: {len(vars_list)} (max 3)")
            return False
        return True
    
    def check_algo(self, algo: AlgoNode) -> bool:
        if not algo:
            return True
        for instr in algo.instructions:
            if not self.check_instr(instr):
                return False
        return True
    
    def check_instr(self, instr: InstrNode) -> bool:
        if isinstance(instr, HaltNode):
            return self.check_halt(instr)
        elif isinstance(instr, PrintNode):
            return self.check_print(instr)
        elif isinstance(instr, CallNode):
            return self.check_call_instr(instr)
        elif isinstance(instr, AssignNode):
            return self.check_assign(instr)
        elif isinstance(instr, LoopNode):
            return self.check_loop(instr)
        elif isinstance(instr, BranchNode):
            return self.check_branch(instr)
        else:
            self.st.add_error(f"Unknown instruction type: {type(instr)}")
            return False
    
    def check_halt(self, halt: HaltNode) -> bool:
        return True
    
    def check_print(self, print_node: PrintNode) -> bool:
        return self.check_output(print_node.output, print_node.is_string)
    
    def check_call_instr(self, call: CallNode) -> bool:
        return self.check_input(call.args)
    
    def check_assign(self, assign: AssignNode) -> bool:
        if assign.is_func_call and isinstance(assign.expr, CallNode):
            return self.check_input(assign.expr.args)
        elif isinstance(assign.expr, TermNode):
            term_type = self.get_term_type(assign.expr)
            if term_type != VarType.NUMERIC:
                self.st.add_error(f"Assignment to '{assign.var}': TERM is not of type 'numeric'")
                return False
            return True
        else:
            self.st.add_error(f"Invalid assignment expression type for '{assign.var}'")
            return False
    
    def check_loop(self, loop: LoopNode) -> bool:
        if loop.condition:
            term_type = self.get_term_type(loop.condition)
            if term_type != VarType.BOOLEAN:
                self.st.add_error(f"Loop condition TERM must be 'boolean', got '{term_type.value}'")
                return False
        algo_correct = self.check_algo(loop.body)
        return algo_correct
    
    def check_branch(self, branch: BranchNode) -> bool:
        if branch.condition:
            term_type = self.get_term_type(branch.condition)
            if term_type not in [VarType.BOOLEAN, VarType.NUMERIC]:
                self.st.add_error(f"Branch condition TERM must be 'boolean' or 'numeric', got '{term_type.value}'")
                return False
        then_correct = self.check_algo(branch.then_branch)
        else_correct = True
        if branch.else_branch:
            else_correct = self.check_algo(branch.else_branch)
        return then_correct and else_correct
    
    def check_output(self, output, is_string: bool) -> bool:
        if is_string:
            return True
        else:
            if isinstance(output, AtomNode):
                atom_type = self.get_atom_type(output)
                if atom_type != VarType.NUMERIC:
                    self.st.add_error("OUTPUT ATOM is not of type 'numeric'")
                    return False
                return True
            else:
                self.st.add_error("Invalid OUTPUT type")
                return False
    
    def check_input(self, args: List[AtomNode]) -> bool:
        if len(args) > 3:
            self.st.add_error(f"Too many arguments in INPUT: {len(args)} (max 3)")
            return False
        for i, arg in enumerate(args):
            atom_type = self.get_atom_type(arg)
            if atom_type != VarType.NUMERIC:
                self.st.add_error(f"INPUT argument {i+1} is not of type 'numeric'")
                return False
        return True
    
    def get_atom_type(self, atom: AtomNode) -> VarType:
        if not atom.is_var:
            return VarType.NUMERIC
        else:
            return VarType.NUMERIC
    
    def get_term_type(self, term: TermNode) -> VarType:
        if isinstance(term, AtomTermNode):
            return self.get_atom_type(term.atom)
        elif isinstance(term, UnopTermNode):
            return self.get_unop_term_type(term)
        elif isinstance(term, BinopTermNode):
            return self.get_binop_term_type(term)
        else:
            self.st.add_error(f"Unknown TERM type: {type(term)}")
            return VarType.TYPELESS
    
    def get_unop_term_type(self, term: UnopTermNode) -> VarType:
        operand_type = self.get_term_type(term.term)
        unop_type = self.get_unop_type(term.op)
        if unop_type == VarType.NUMERIC and operand_type == VarType.NUMERIC:
            return VarType.NUMERIC
        elif unop_type == VarType.BOOLEAN:
            if operand_type in [VarType.BOOLEAN, VarType.NUMERIC]:
                return VarType.BOOLEAN
            else:
                self.st.add_error(f"UNOP '{term.op}' requires 'boolean' or 'numeric' operand, got '{operand_type.value}'")
                return VarType.TYPELESS
        else:
            self.st.add_error(f"UNOP '{term.op}' type mismatch: operator is {unop_type.value}, operand is {operand_type.value}")
            return VarType.TYPELESS
    
    def get_binop_term_type(self, term: BinopTermNode) -> VarType:
        left_type = self.get_term_type(term.left)
        right_type = self.get_term_type(term.right)
        binop_type = self.get_binop_type(term.op)
        if binop_type == VarType.NUMERIC:
            if left_type == VarType.NUMERIC and right_type == VarType.NUMERIC:
                return VarType.NUMERIC
            else:
                self.st.add_error(f"Numeric BINOP '{term.op}' requires both operands to be 'numeric', got {left_type.value} and {right_type.value}")
                return VarType.TYPELESS
        elif binop_type == VarType.BOOLEAN:
            if left_type == VarType.BOOLEAN and right_type == VarType.BOOLEAN:
                return VarType.BOOLEAN
            else:
                self.st.add_error(f"Boolean BINOP '{term.op}' requires operands to be 'boolean' or 'numeric', got {left_type.value} and {right_type.value}")
                return VarType.TYPELESS
        elif binop_type == VarType.COMPARISON:
            if left_type == VarType.NUMERIC and right_type == VarType.NUMERIC:
                return VarType.BOOLEAN
            else:
                self.st.add_error(f"Comparison BINOP '{term.op}' requires both operands to be 'numeric', got {left_type.value} and {right_type.value}")
                return VarType.TYPELESS
        else:
            self.st.add_error(f"Unknown BINOP type for '{term.op}': {binop_type.value}")
            return VarType.TYPELESS
    
    def get_unop_type(self, op: str) -> VarType:
        if op == 'neg':
            return VarType.NUMERIC
        elif op == 'not':
            return VarType.BOOLEAN
        else:
            self.st.add_error(f"Unknown UNOP: {op}")
            return VarType.TYPELESS
    
    def get_binop_type(self, op: str) -> VarType:
        if op in ['>', 'eq']:
            return VarType.COMPARISON
        elif op in ['or', 'and']:
            return VarType.BOOLEAN
        elif op in ['plus', 'minus', 'mult', 'div']:
            return VarType.NUMERIC
        else:
            self.st.add_error(f"Unknown BINOP: {op}")
            return VarType.TYPELESS

# ============================================================================
# CODE GENERATOR - NON-INLINED, BASIC-COMPATIBLE SUBROUTINES (GOSUB/RETURN)
# ============================================================================

class CodeGenerator:
    def __init__(self, ast: ProgramNode, symbol_table: SymbolTable):
        self.ast = ast
        self.st = symbol_table
        self.code: List[str] = []
        self.temp_counter = 0
        self.label_counter = 0

    def new_temp(self) -> str:
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def new_label(self) -> str:
        self.label_counter += 1
        return f"l{self.label_counter}"

    def emit(self, s: str):
        self.code.append(s)

    def generate(self) -> List[str]:
        """
        Emit intermediate BASIC-like code with labels (using "label:"), no REM.
        - Subroutines (procedures/functions) are placed first.
        - Main is placed after, with initial GOTO mainstart to avoid fallthrough.
        Final numeric line mapping is done in process_labels_and_jumps().
        """
        if not self.ast:
            return []
        self.code = []

        # Emit procedures
        for p in self.ast.procedures:
            self.emit(f"proc_{p.name}:")  # internal label; will be removed, mapped to numbers
            # Parameter load variables inside subroutine are named <name><param>
            # We expect caller to assign arg<name>1.. before GOSUB. Here we copy to locals if needed.
            # We keep it simple: directly use <name><param> as the working vars.
            for idx, param in enumerate(p.params, start=1):
                self.emit(f"{p.name}{param} = arg{p.name}{idx}")
            for lv in p.local_vars:
                # locals don't need explicit init, but we keep the name scheme
                pass
            if p.body:
                self.generate_algo(p.body, owner=('proc', p.name))
            self.emit("RETURN")

        # Emit functions
        for f in self.ast.functions:
            self.emit(f"func_{f.name}:")
            for idx, param in enumerate(f.params, start=1):
                self.emit(f"{f.name}{param} = arg{f.name}{idx}")
            for lv in f.local_vars:
                pass
            if f.body:
                self.generate_algo(f.body, owner=('func', f.name))
            # Function return value goes into retn
            if f.return_atom is not None:
                if f.return_atom.is_var:
                    self.emit(f"ret{f.name} = {f.name}{f.return_atom.value if f.return_atom.value in f.params + f.local_vars else f.return_atom.value}")
                else:
                    self.emit(f"ret{f.name} = {f.return_atom.value}")
            else:
                self.emit(f"ret{f.name} = 0")
            self.emit("RETURN")

        # Emit main
        self.emit("gotomain:")  # landing label for main start
        if self.ast.main and self.ast.main.body:
            # initial jump over subroutines
            # We'll add the GOTO to gotomain at the very top after we know labels.
            pass
        # Insert initial jump at top now that labels exist
        # We'll reorder by adding this at the beginning after everything else
        main_block: List[str] = []
        # main variable prefixing is not necessary here; names are kept as-is
        if self.ast.main and self.ast.main.body:
            self.generate_algo(self.ast.main.body, owner=('main', None), out=main_block)
        # Place the initial jump and subroutines before main
        self.code = [f"GOTO gotomain"] + self.code + ["gotomain:"] + main_block

        return self.code

    def generate_algo(self, algo: AlgoNode, owner: Tuple[str, Optional[str]], out: Optional[List[str]] = None):
        sink = out if out is not None else self.code
        for instr in algo.instructions:
            for line in self.generate_instruction(instr, owner):
                sink.append(line)

    def generate_instruction(self, instr: InstrNode, owner: Tuple[str, Optional[str]]) -> List[str]:
        out: List[str] = []
        kind, name = owner

        if isinstance(instr, HaltNode):
            out.append("STOP")

        elif isinstance(instr, PrintNode):
            if instr.is_string:
                out.append(f"PRINT {instr.output}")
            else:
                val = self.generate_atom(instr.output, owner)
                out.append(f"PRINT {val}")

        elif isinstance(instr, AssignNode):
            if instr.is_func_call and isinstance(instr.expr, CallNode):
                # x = CALL f(args)
                fname = instr.expr.name
                # prepare args
                for idx, a in enumerate(instr.expr.args, start=1):
                    rhs = self.generate_atom(a, owner)
                    out.append(f"arg{fname}{idx} = {rhs}")
                # gosub
                out.append(f"GOSUB func_{fname}")
                # assign result
                out.append(f"{self.map_var(instr.var, owner)} = ret{fname}")
            else:
                t = self.generate_term(instr.expr, owner, out)
                out.append(f"{self.map_var(instr.var, owner)} = {t}")

        elif isinstance(instr, CallNode):
            # CALL p(args)
            pname = instr.name
            for idx, a in enumerate(instr.args, start=1):
                rhs = self.generate_atom(a, owner)
                out.append(f"arg{pname}{idx} = {rhs}")
            out.append(f"GOSUB proc_{pname}")

        elif isinstance(instr, BranchNode):
            label_t = self.new_label()
            label_exit = self.new_label()
            cond_line = self.generate_condition(instr.condition, label_t, owner, out)
            out.append(cond_line)
            if instr.else_branch:
                # else block first
                if instr.else_branch:
                    self.generate_algo(instr.else_branch, owner, out)
                out.append(f"GOTO {label_exit}")
                out.append(f"{label_t}:")
                if instr.then_branch:
                    self.generate_algo(instr.then_branch, owner, out)
                out.append(f"{label_exit}:")
            else:
                out.append(f"GOTO {label_exit}")
                out.append(f"{label_t}:")
                if instr.then_branch:
                    self.generate_algo(instr.then_branch, owner, out)
                out.append(f"{label_exit}:")

        elif isinstance(instr, LoopNode):
            if instr.is_while:
                label_start = self.new_label()
                label_body = self.new_label()
                label_exit = self.new_label()
                out.append(f"{label_start}:")
                cond_line = self.generate_condition(instr.condition, label_body, owner, out)
                out.append(cond_line)
                out.append(f"GOTO {label_exit}")
                out.append(f"{label_body}:")
                if instr.body:
                    self.generate_algo(instr.body, owner, out)
                out.append(f"GOTO {label_start}")
                out.append(f"{label_exit}:")
            else:
                label_start = self.new_label()
                label_exit = self.new_label()
                out.append(f"{label_start}:")
                if instr.body:
                    self.generate_algo(instr.body, owner, out)
                cond_line = self.generate_condition(instr.condition, label_exit, owner, out)
                out.append(cond_line)
                out.append(f"GOTO {label_start}")
                out.append(f"{label_exit}:")
        return out

    def generate_condition(self, term: TermNode, true_label: str, owner: Tuple[str, Optional[str]], out: List[str]) -> str:
        if isinstance(term, BinopTermNode) and term.op in ['eq', '>']:
            l = self.generate_term(term.left, owner, out)
            r = self.generate_term(term.right, owner, out)
            op = '=' if term.op == 'eq' else '>'
            return f"IF {l} {op} {r} THEN {true_label}"
        t = self.generate_term(term, owner, out)
        return f"IF {t} THEN {true_label}"

    def generate_term(self, term: TermNode, owner: Tuple[str, Optional[str]], out: List[str]) -> str:
        if isinstance(term, AtomTermNode):
            return self.generate_atom(term.atom, owner)
        elif isinstance(term, UnopTermNode):
            inner = self.generate_term(term.term, owner, out)
            t = self.new_temp()
            if term.op == 'neg':
                out.append(f"{t} = - {inner}")
            elif term.op == 'not':
                out.append(f"{t} = NOT {inner}")
            else:
                out.append(f"{t} = {inner}")
            return t
        elif isinstance(term, BinopTermNode):
            l = self.generate_term(term.left, owner, out)
            r = self.generate_term(term.right, owner, out)
            t = self.new_temp()
            op_map = {'plus': '+', 'minus': '-', 'mult': '*', 'div': '/',
                      'eq': '=', '>': '>', 'and': 'AND', 'or': 'OR'}
            op = op_map.get(term.op, term.op.upper())
            out.append(f"{t} = {l} {op} {r}")
            return t
        return "0"

    def generate_atom(self, atom: AtomNode, owner: Tuple[str, Optional[str]]) -> str:
        if atom.is_var:
            return self.map_var(atom.value, owner)
        else:
            return str(atom.value)

    def map_var(self, var: str, owner: Tuple[str, Optional[str]]) -> str:
        kind, name = owner
        # temps stay as is (t1, t2...), digits only afterwards
        if var.startswith('t') and var[1:].isdigit():
            return var
        if kind == 'proc' and name:
            # params/locals of proc are referenced as <procname><var> when applicable
            return f"{name}{var}" if var in self._proc_nameset(name) else var
        if kind == 'func' and name:
            return f"{name}{var}" if var in self._func_nameset(name) else var
        # main/global as-is
        return var

    def _proc_nameset(self, name: str) -> Set[str]:
        p = next((x for x in self.ast.procedures if x.name == name), None)
        return set(p.params + p.local_vars) if p else set()

    def _func_nameset(self, name: str) -> Set[str]:
        f = next((x for x in self.ast.functions if x.name == name), None)
        return set(f.params + f.local_vars) if f else set()

# ============================================================================
# LABEL AND JUMP PROCESSING (no REM, numeric mapping, includes GOSUB)
# ============================================================================

def process_labels_and_jumps(intermediate_code: List[str]) -> Tuple[List[str], Dict[str, int]]:
    """
    Process labels and resolve jumps to numeric targets without emitting REM lines.
    - Lines ending with ':' define a label for the *next* executable line number.
    - Supported control transfers: GOTO <label|num>, GOSUB <label|num>, IF ... THEN <label|num>
    - Label declaration lines are DROPPED (not emitted).
    - Output keeps original 1..N numbering that your driver prints (we don't add 10s here).
    """
    # First pass: determine which lines will actually be emitted and where labels point
    label_map: Dict[str, int] = {}
    executable_flags: List[bool] = []  # per original line, whether it will be emitted
    stripped_lines: List[str] = []

    # mark which original lines are labels (to be dropped)
    for line in intermediate_code:
        s = line.strip()
        is_label = s.endswith(':')
        executable_flags.append(not is_label)
        stripped_lines.append(s)

    # determine numeric indices (1-based) of emitted lines
    emitted_index = 1
    line_number_of_emitted: List[Optional[int]] = []
    for is_exec in executable_flags:
        if is_exec:
            line_number_of_emitted.append(emitted_index)
            emitted_index += 1
        else:
            line_number_of_emitted.append(None)

    # map labels to the line number of the *next* emitted line
    # (i.e., the first executable line after the label)
    next_exec_after: Dict[int, int] = {}
    next_num = None
    for i in reversed(range(len(stripped_lines))):
        if executable_flags[i]:
            next_num = line_number_of_emitted[i]
        else:
            # label line: map to the next executable number seen so far
            label_name = stripped_lines[i][:-1].strip()
            if next_num is None:
                # label at end: map to the next sequential number after all lines
                next_num = emitted_index
            label_map[label_name] = next_num

    # Second pass: emit lines with label references resolved
    final_code: List[str] = []
    for i, s in enumerate(stripped_lines):
        if not executable_flags[i]:
            continue  # drop label lines

        # resolve GOTO/GOSUB/THEN
        out_line = s

        # GOTO
        if s.startswith("GOTO "):
            tgt = s[len("GOTO "):].strip()
            if tgt in label_map:
                out_line = f"GOTO {label_map[tgt]}"

        # GOSUB
        elif s.startswith("GOSUB "):
            tgt = s[len("GOSUB "):].strip()
            if tgt in label_map:
                out_line = f"GOSUB {label_map[tgt]}"

        # IF ... THEN ...
        elif s.startswith("IF "):
            if "THEN" in s:
                left, right = s.split("THEN", 1)
                tgt = right.strip()
                if tgt in label_map:
                    out_line = f"{left}THEN {label_map[tgt]}"

        final_code.append(out_line)

    return final_code, label_map

# ============================================================================
# MAIN COMPILER
# ============================================================================

def compile_spl_with_antlr(source_code: str, output_file: str = None) -> bool:
    """SPL compilation using ANTLR parser (fallbacks to handwritten if ANTLR unavailable)"""
    try:
        from antlr4 import InputStream, CommonTokenStream
        from SPLLexer import SPLLexer
        from SPLParser import SPLParser
        from SPLASTVisitor import SPLASTVisitor
        ANTLR_AVAILABLE = True
    except Exception:
        ANTLR_AVAILABLE = False

    if not ANTLR_AVAILABLE:
        print("ANTLR not available! Falling back to hand-written parser.")
        return compile_spl(source_code, output_file)
    
    try:
        print("Phase 1-2: ANTLR Lexical and Syntax Analysis...")
        input_stream = InputStream(source_code)
        lexer = SPLLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = SPLParser(stream)
        tree = parser.spl_prog()
        
        symbol_table = SymbolTable()
        visitor = SPLASTVisitor(symbol_table)
        ast = visitor.visit(tree)
        return continue_compilation(ast, symbol_table, output_file)
        
    except Exception as e:
        print(f"ANTLR parsing failed: {e}")
        return False

def compile_spl(source_code: str, output_file: str = None) -> bool:
    print("Phase 1: Lexical Analysis...")
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()

    print("\nTokens accepted", end="\n\n")
    
    print("Phase 2: Syntax Analysis...")
    symbol_table = SymbolTable()
    parser = Parser(tokens, symbol_table)
    ast = parser.parse()
    
    if symbol_table.has_errors():
        print("Syntax error:")
        symbol_table.print_report()
        return False
    else:
        print("\nSyntax accepted", end="\n\n")

    return continue_compilation(ast, symbol_table, output_file)

def continue_compilation(ast: ProgramNode, symbol_table: SymbolTable, output_file: str = None) -> bool:
    print("Phase 3: NAME-SCOPE-RULES Analysis...")
    scope_analyzer = ScopeAnalyzer(ast, symbol_table)
    scope_analyzer.analyze()
    scope_analyzer.print_symbol_table_report()
    
    if symbol_table.has_errors():
        print("Naming error:")
        symbol_table.print_report()
        return False
    else:
        print("\nVariable Naming and Function Naming accepted", end="\n\n")
    
    type_analyzer = TypeAnalyzer(ast, symbol_table)
    is_correctly_typed = type_analyzer.analyze()
    
    if not is_correctly_typed or symbol_table.has_errors():
        print("Type error:")
        symbol_table.print_report()
        return False
    else: 
        print("\nTypes accepted", end="\n\n")
    
    print("Phase 5: Code Generation...")
    code_generator = CodeGenerator(ast, symbol_table)
    intermediate_code = code_generator.generate()
    
    symbol_table.print_report()
    
    print("\n=== INTERMEDIATE CODE (Before Label Processing) ===")
    for i, line in enumerate(intermediate_code, 1):
        print(f"{i:4d}: {line}")
    
    print("\n=== PHASE 6: Processing Labels and Jumps ===")
    final_code, label_map = process_labels_and_jumps(intermediate_code)
    
    if label_map:
        print("\nLabel Mapping:")
        for label, line_num in sorted(label_map.items(), key=lambda x: x[1]):
            print(f"  {label:15s} -> Line {line_num}")
    else:
        print("No labels found in code.")
    
    print("\n=== FINAL EXECUTABLE CODE ===")
    for i, line in enumerate(final_code, 1):
        print(f"{i:4d}: {line}")
    
    if output_file:
        with open(output_file, 'w') as f:
            for i, line in enumerate(final_code, 1):
                if line.strip():
                    f.write(f"{i}: {line}\n")
        print(f"\nFinal executable code written to {output_file}")
    
    return True

def main():
    use_antlr = "--use-antlr" in sys.argv
    if use_antlr:
        sys.argv.remove("--use-antlr")
    
    if len(sys.argv) != 3:
        print("Usage: python compiler.py input.spl output.txt [--use-antlr]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        with open(input_file, 'r') as f:
            source_code = f.read()
        
        if use_antlr:
            success = compile_spl_with_antlr(source_code, output_file)
        else:
            success = compile_spl(source_code, output_file)
        
        if success:
            print("Compilation successful!")
            sys.exit(0)
        else:
            print("Compilation failed!")
            sys.exit(1)
            
    except FileNotFoundError:
        print(f"Error: Could not find input file '{input_file}'")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
