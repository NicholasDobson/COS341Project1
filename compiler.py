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
        return f"_t{self.temp_counter}"
        
    def new_label(self) -> str:
        self.label_counter += 1
        return f"_L{self.label_counter}"
    
    # ========================================================================
    # SCOPE MANAGEMENT - Scope Stack Operations
    # ========================================================================
    
    def push_scope(self, scope_type: ScopeType, name: str = "", context: Dict[str, Any] = None):
        """
        Push a new scope onto the scope stack.
        
        Args:
            scope_type: Type of scope (GLOBAL, LOCAL, MAIN, etc.)
            name: Optional name for the scope (e.g., function/procedure name)
            context: Optional additional context information
        """
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
        """
        Pop the current scope from the stack.
        
        Returns:
            The popped scope information, or None if stack is empty
        """
        if not self.scope_stack:
            return None
        
        popped = self.scope_stack.pop()
        self.current_scope_type = self.scope_stack[-1]['type'] if self.scope_stack else None
        return popped
    
    def current_scope(self) -> Optional[Dict[str, Any]]:
        """Get the current scope without popping it."""
        return self.scope_stack[-1] if self.scope_stack else None
    
    def get_current_scope_type(self) -> Optional[ScopeType]:
        """Get the current scope type."""
        return self.current_scope_type
    
    def scope_depth(self) -> int:
        """Get the current scope stack depth."""
        return len(self.scope_stack)
    
    def get_parent_scope(self) -> Optional[Dict[str, Any]]:
        """Get the parent scope of the current scope."""
        if len(self.scope_stack) >= 2:
            return self.scope_stack[-2]
        return None
    
    # ========================================================================
    # CRUD OPERATIONS
    # ========================================================================
    
    def add_error(self, msg: str):
        """Add an error message to the error list."""
        self.errors.append(f"ERROR: {msg}")
    
    def add_type_error(self, msg: str, line: int = 0):
        """Add a formatted type error."""
        if line:
            self.errors.append(f"ERROR (Line {line}): TYPE-ERROR: {msg}")
        else:
            self.errors.append(f"ERROR: TYPE-ERROR: {msg}")
    
    def add_name_error(self, msg: str, line: int = 0):
        """Add a formatted name-rule violation error."""
        if line:
            self.errors.append(f"ERROR (Line {line}): NAME-RULE-VIOLATION: {msg}")
        else:
            self.errors.append(f"ERROR: NAME-RULE-VIOLATION: {msg}")
        
    def add_warning(self, msg: str):
        """Add a warning message to the warning list."""
        self.warnings.append(f"WARNING: {msg}")
    
    # CREATE
    def add_symbol(self, symbol: SymbolInfo) -> bool:
        """
        Add a symbol to the symbol table.
        
        Args:
            symbol: The SymbolInfo object to add
            
        Returns:
            True if successful, False if node_id already exists
        """
        if symbol.node_id in self.symbols:
            self.add_warning(f"Attempted to add duplicate node_id {symbol.node_id}")
            return False
        
        self.symbols[symbol.node_id] = symbol
        
        # Update secondary index
        if symbol.name not in self.var_lookup:
            self.var_lookup[symbol.name] = []
        self.var_lookup[symbol.name].append(symbol)
        
        # Add to current scope if scope stack is active
        if self.scope_stack:
            self.scope_stack[-1]['symbols'].append(symbol.node_id)
        
        return True
    
    # READ
    def get_symbol(self, node_id: int) -> Optional[SymbolInfo]:
        """
        Retrieve a symbol by its node_id.
        
        Args:
            node_id: The unique identifier of the symbol
            
        Returns:
            The SymbolInfo object, or None if not found
        """
        return self.symbols.get(node_id)
    
    def lookup_var(self, name: str, scope_context: ScopeType = None) -> Optional[SymbolInfo]:
        """
        Lookup variable by name with proper scope resolution.
        
        Args:
            name: Variable name to lookup
            scope_context: The scope context for resolution (None = use current)
            
        Returns:
            The most appropriate SymbolInfo, or None if not found
        """
        if name not in self.var_lookup:
            return None
        
        # If no scope context provided, use current scope
        if scope_context is None:
            scope_context = self.current_scope_type
        
        # If still no scope context, return most recent
        if scope_context is None:
            return self.var_lookup[name][-1] if self.var_lookup[name] else None
        
        # Search with scope resolution rules
        for sym in reversed(self.var_lookup[name]):
            if scope_context == ScopeType.LOCAL:
                # In local scope: can see local vars, parameters, and global vars
                if sym.is_local or sym.is_parameter or sym.is_global:
                    return sym
            elif scope_context == ScopeType.MAIN:
                # In main scope: can see main vars and global vars
                if sym.is_main_var or sym.is_global:
                    return sym
            elif scope_context == ScopeType.GLOBAL:
                # In global scope: only global vars
                if sym.is_global:
                    return sym
            elif scope_context == ScopeType.PROCEDURE or scope_context == ScopeType.FUNCTION:
                # In procedure/function scope: same as local
                if sym.is_local or sym.is_parameter or sym.is_global:
                    return sym
        
        return None
    
    def get_symbol_by_name(self, name: str, scope: ScopeType = None) -> Optional[SymbolInfo]:
        """
        Get symbol by name, optionally filtered by scope.
        
        Args:
            name: Variable name
            scope: Optional scope filter
            
        Returns:
            First matching symbol, or None
        """
        if name not in self.var_lookup:
            return None
        
        symbols = self.var_lookup[name]
        if scope:
            symbols = [s for s in symbols if s.scope == scope]
        
        return symbols[0] if symbols else None
    
    def get_all_symbols_in_scope(self, scope: ScopeType) -> List[SymbolInfo]:
        """Get all symbols in a specific scope type."""
        return [s for s in self.symbols.values() if s.scope == scope]
    
    # UPDATE
    def update_symbol(self, node_id: int, **kwargs) -> bool:
        """
        Update symbol fields.
        
        Args:
            node_id: The symbol's node_id
            **kwargs: Field names and new values
            
        Returns:
            True if successful, False if symbol not found
        """
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
        """
        Delete a symbol and clean up all references.
        
        Args:
            node_id: The symbol's unique identifier
            
        Returns:
            True if successful, False if symbol not found
        """
        if node_id not in self.symbols:
            return False
        
        symbol = self.symbols[node_id]
        
        # Remove from var_lookup
        if symbol.name in self.var_lookup:
            self.var_lookup[symbol.name] = [
                s for s in self.var_lookup[symbol.name] 
                if s.node_id != node_id
            ]
            # Clean up empty entries
            if not self.var_lookup[symbol.name]:
                del self.var_lookup[symbol.name]
        
        # Remove from scope stack if present
        for scope in self.scope_stack:
            if node_id in scope['symbols']:
                scope['symbols'].remove(node_id)
        
        # Remove from symbols dict
        del self.symbols[node_id]
        return True
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def clear(self):
        """Clear all symbol table data."""
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
            # self.pos += 1  # Don't skip - this should be an error
            
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
        """
        SPL Vocabulary Rule 4: string - any sequence of digits or letters between quotation marks
        Max length 15 (but allowing 50 for tests as requested)
        """
        start_line = self.line
        start = self.pos
        self.pos += 1  # skip opening "
        count = 0
        while self.pos < len(self.text) and self.text[self.pos] != '"' and count < 50:  # Max 50 for tests
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
        """
        SPL Vocabulary Rule 3: ( 0 | [1...9][0...9]* )
        Numbers can be 0 or start with 1-9 followed by any digits
        """
        start = self.pos
        start_line = self.line
        
        if self.text[self.pos] == '0':
            # Single zero
            self.pos += 1
            # Check if followed by more digits (not allowed)
            if self.pos < len(self.text) and self.text[self.pos].isdigit():
                raise ValueError(f"Invalid number format: leading zero not allowed except for '0' at line {start_line}")
        else:
            # Must start with 1-9
            if not (self.text[self.pos].isdigit() and self.text[self.pos] != '0'):
                raise ValueError(f"Invalid number format at line {start_line}")
            self.pos += 1
            # Followed by any digits [0-9]*
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
                
        return Token('NUMBER', self.text[start:self.pos], start_line)
        
    def read_identifier(self) -> Token:
        """
        SPL Vocabulary Rules:
        1. User-defined-name may not be identical with any green keyword
        2. User-defined-name: [a-z]{a-z}*{0-9}* (at least one letter a-z, followed by any letters a-z, followed by any digits 0-9)
        """
        start = self.pos
        start_line = self.line
        
        # Must start with [a-z] - this should be guaranteed by the caller
        if self.pos >= len(self.text) or not self.text[self.pos].islower():
            raise ValueError(f"Invalid identifier start at position {self.pos}")
        
        # [a-z]+ (at least one, then any number of lowercase letters)
        while self.pos < len(self.text) and self.text[self.pos].islower():
            self.pos += 1
        
        # [0-9]* (any number of digits)
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1
            
        value = self.text[start:self.pos]
        
        # Ensure we consumed at least one character
        if len(value) == 0:
            raise ValueError(f"Empty identifier at position {start}")
            
        # SPL Vocabulary Rule 1: Check if it conflicts with keywords
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
                        # Not a function call, restore and parse as term
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
            
            # Check for unop (prefix: ( neg TERM ) or ( not TERM ))
            if self.match('neg') or self.match('not'):
                node = UnopTermNode(node_id=self.st.get_node_id(), line=self.current().line)
                node.op = self.consume().value
                node.term = self.parse_term()
                self.consume(')')
                return node
            
            # Check for binary operator first (prefix: ( BINOP TERM TERM ))
            if self.current().value in ['eq', '>', 'or', 'and', 'plus', 'minus', 'mult', 'div']:
                node = BinopTermNode(node_id=self.st.get_node_id(), line=self.current().line)
                node.op = self.consume().value
                node.left = self.parse_term()
                node.right = self.parse_term()
                self.consume(')')
                return node
            
            # Parse first term for infix check
            left_term = self.parse_term()
            
            # Check if next token is a binary operator (infix: ( TERM BINOP TERM ))
            if self.current().value in ['eq', '>', 'or', 'and', 'plus', 'minus', 'mult', 'div']:
                node = BinopTermNode(node_id=self.st.get_node_id(), line=self.current().line)
                node.left = left_term
                node.op = self.consume().value
                node.right = self.parse_term()
                self.consume(')')
                return node
            
            # If no binary operator, it's just a parenthesized term
            self.consume(')')
            return left_term
            
        # Atom
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
        """
        Implements the NAME-SCOPE-RULES for SPL as specified.
        The entire SPL_PROG forms the "Everywhere" scope.
        """
        if not self.ast:
            return
            
        print("Starting NAME-SCOPE-RULES analysis...")
        
        # Phase 1: Establish "Everywhere" scope and collect all names
        self.collect_everywhere_scope_names()
        
        # Phase 2: Check "Everywhere" scope name conflicts
        self.check_everywhere_scope_conflicts()
        
        # Phase 3: Analyze each scope in detail
        self.analyze_global_scope()
        self.analyze_procedure_scope()
        self.analyze_function_scope()
        self.analyze_main_scope()
        
        print("NAME-SCOPE-RULES analysis completed.")
    
    def collect_everywhere_scope_names(self):
        """
        Collect all names from the "Everywhere" scope:
        - Global variables from VARIABLES
        - Procedure names from PROCDEFS
        - Function names from FUNCDEFS
        """
        # Collect global variables
        for var in self.ast.variables:
            if var in self.global_variables:
                self.emit_name_rule_violation(f"double-declaration: Duplicate global variable declaration: '{var}'")
            else:
                self.global_variables.add(var)
                self.st.global_vars.add(var)
                # Add to symbol table with node ID
                symbol = SymbolInfo(
                    name=var,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.GLOBAL,
                    var_type=VarType.TYPELESS,
                    is_global=True
                )
                self.st.add_symbol(symbol)
        
        # Collect procedure names
        for proc in self.ast.procedures:
            if proc.name in self.procedure_names:
                self.emit_name_rule_violation(f"double-declaration: Duplicate procedure declaration: '{proc.name}'")
            else:
                self.procedure_names.add(proc.name)
                self.st.procedures[proc.name] = FunctionInfo(
                    proc.name, proc.params, proc, is_procedure=True
                )
        
        # Collect function names
        for func in self.ast.functions:
            if func.name in self.function_names:
                self.emit_name_rule_violation(f"double-declaration: Duplicate function declaration: '{func.name}'")
            else:
                self.function_names.add(func.name)
                self.st.functions[func.name] = FunctionInfo(
                    func.name, func.params, func, is_procedure=False
                )
    
    def check_everywhere_scope_conflicts(self):
        """
        Check NAME-SCOPE-RULES for "Everywhere" scope:
        - NO variable name may be identical with any function name
        - NO variable name may be identical with any procedure name  
        - NO function name may be identical with any procedure name
        """
        # Check variable vs function conflicts
        var_func_conflicts = self.global_variables & self.function_names
        for name in var_func_conflicts:
            self.emit_name_rule_violation(f"Variable name '{name}' conflicts with function name")
        
        # Check variable vs procedure conflicts
        var_proc_conflicts = self.global_variables & self.procedure_names
        for name in var_proc_conflicts:
            self.emit_name_rule_violation(f"Variable name '{name}' conflicts with procedure name")
        
        # Check function vs procedure conflicts
        func_proc_conflicts = self.function_names & self.procedure_names
        for name in func_proc_conflicts:
            self.emit_name_rule_violation(f"Function name '{name}' conflicts with procedure name")
    
    def analyze_global_scope(self):
        """
        Analyze the "Global" scope formed by VARIABLES node.
        Rule: No two VAR names are allowed to be identical.
        """
        # Already handled in collect_everywhere_scope_names()
        pass
    
    def analyze_procedure_scope(self):
        """
        Analyze the "Procedure" scope formed by PROCDEFS node.
        Rule: No two PDEF-names are allowed to be identical.
        """
        # Already handled in collect_everywhere_scope_names()
        
        # Now analyze each individual procedure's local scope
        for proc in self.ast.procedures:
            self.analyze_procedure_local_scope(proc)
    
    def analyze_function_scope(self):
        """
        Analyze the "Function" scope formed by FUNCDEFS node.
        Rule: No two FDEF-names are allowed to be identical.
        """
        # Already handled in collect_everywhere_scope_names()
        
        # Now analyze each individual function's local scope
        for func in self.ast.functions:
            self.analyze_function_local_scope(func)
    
    def analyze_main_scope(self):
        """
        Analyze the "Main" scope formed by MAINPROG node.
        Rule: No two VAR-names in VARIABLES are allowed to be identical.
        """
        if not self.ast.main:
            return
            
        main_vars = set()
        for var in self.ast.main.variables:
            if var in main_vars:
                self.emit_name_rule_violation(f"double-declaration: Duplicate variable declaration in main: '{var}'")
            else:
                main_vars.add(var)
                # Add to symbol table
                symbol = SymbolInfo(
                    name=var,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.MAIN,
                    var_type=VarType.TYPELESS,
                    is_main_var=True
                )
                self.st.add_symbol(symbol)
        
        # Analyze variables used in main's ALGO
        if self.ast.main.body:
            self.analyze_algo_variables(self.ast.main.body, ScopeType.MAIN, 
                                      params=[], local_vars=[], main_vars=list(main_vars))
    
    def analyze_procedure_local_scope(self, proc: ProcDefNode):
        """
        Analyze a procedure's "Local" scope.
        Rules:
        - No VAR-name in MAXTHREE may be identical with any VAR-name in PARAM
        - No two VAR-names in MAXTHREE are allowed to be identical
        """
        # Check for duplicate parameters
        param_set = set()
        for param in proc.params:
            if param in param_set:
                self.emit_name_rule_violation(f"double-declaration: Duplicate parameter in procedure '{proc.name}': '{param}'")
            else:
                param_set.add(param)
                # Add parameter to symbol table
                symbol = SymbolInfo(
                    name=param,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.LOCAL,
                    var_type=VarType.TYPELESS,
                    is_parameter=True,
                    procedure_name=proc.name
                )
                self.st.add_symbol(symbol)
        
        # Check for duplicate local variables
        local_set = set()
        for local_var in proc.local_vars:
            if local_var in local_set:
                self.emit_name_rule_violation(f"double-declaration: Duplicate local variable in procedure '{proc.name}': '{local_var}'")
            elif local_var in param_set:
                self.emit_name_rule_violation(f"shadowing: Local variable '{local_var}' shadows parameter in procedure '{proc.name}'")
            else:
                local_set.add(local_var)
                # Add local variable to symbol table
                symbol = SymbolInfo(
                    name=local_var,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.LOCAL,
                    var_type=VarType.TYPELESS,
                    is_local=True,
                    procedure_name=proc.name
                )
                self.st.add_symbol(symbol)
        
        # Analyze variables used in procedure's ALGO
        if proc.body:
            self.analyze_algo_variables(proc.body, ScopeType.LOCAL, 
                                      params=list(param_set), local_vars=list(local_set), 
                                      procedure_name=proc.name)
    
    def analyze_function_local_scope(self, func: FuncDefNode):
        """
        Analyze a function's "Local" scope.
        Same rules as procedure local scope.
        """
        # Check for duplicate parameters
        param_set = set()
        for param in func.params:
            if param in param_set:
                self.emit_name_rule_violation(f"double-declaration: Duplicate parameter in function '{func.name}': '{param}'")
            else:
                param_set.add(param)
                # Add parameter to symbol table
                symbol = SymbolInfo(
                    name=param,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.LOCAL,
                    var_type=VarType.TYPELESS,
                    is_parameter=True,
                    function_name=func.name
                )
                self.st.add_symbol(symbol)
        
        # Check for duplicate local variables
        local_set = set()
        for local_var in func.local_vars:
            if local_var in local_set:
                self.emit_name_rule_violation(f"double-declaration: Duplicate local variable in function '{func.name}': '{local_var}'")
            elif local_var in param_set:
                self.emit_name_rule_violation(f"shadowing: Local variable '{local_var}' shadows parameter in function '{func.name}'")
            else:
                local_set.add(local_var)
                # Add local variable to symbol table
                symbol = SymbolInfo(
                    name=local_var,
                    node_id=self.st.get_node_id(),
                    scope=ScopeType.LOCAL,
                    var_type=VarType.TYPELESS,
                    is_local=True,
                    function_name=func.name
                )
                self.st.add_symbol(symbol)
        
        # Analyze variables used in function's ALGO
        if func.body:
            self.analyze_algo_variables(func.body, ScopeType.LOCAL, 
                                      params=list(param_set), local_vars=list(local_set), 
                                      function_name=func.name)
        
        # Analyze return atom
        if func.return_atom and func.return_atom.is_var:
            self.check_variable_declaration(func.return_atom.value, ScopeType.LOCAL, 
                                          params=list(param_set), local_vars=list(local_set),
                                          main_vars=[], function_name=func.name)
    
    def analyze_algo_variables(self, algo: AlgoNode, current_scope: ScopeType, 
                             params: List[str] = None, local_vars: List[str] = None,
                             main_vars: List[str] = None, procedure_name: str = None,
                             function_name: str = None):
        """
        Analyze all variables used in an ALGO according to NAME-SCOPE-RULES.
        """
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
        """
        Analyze variables in a single instruction according to NAME-SCOPE-RULES.
        """
        if isinstance(instr, AssignNode):
            # Check assigned variable
            self.check_variable_declaration(instr.var, current_scope, params, local_vars, 
                                          main_vars, procedure_name, function_name)
            
            # Check expression variables
            if isinstance(instr.expr, TermNode):
                self.analyze_term_variables(instr.expr, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
            elif instr.is_func_call and isinstance(instr.expr, CallNode):
                self.analyze_call_variables(instr.expr, current_scope, params, local_vars,
                                          main_vars, procedure_name, function_name)
                
        elif isinstance(instr, CallNode):
            # Check procedure/function call arguments
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
        """Analyze variables in function/procedure call arguments."""
        # First, check if the called procedure/function is declared
        if call.name not in self.procedure_names and call.name not in self.function_names:
            self.st.add_error(f"undeclared: Undeclared procedure or function: '{call.name}'")
        
        # Then check the arguments
        for arg in call.args:
            if arg.is_var:
                self.check_variable_declaration(arg.value, current_scope, params, local_vars,
                                              main_vars, procedure_name, function_name)
    
    def analyze_term_variables(self, term: TermNode, current_scope: ScopeType,
                             params: List[str], local_vars: List[str], main_vars: List[str],
                             procedure_name: str = None, function_name: str = None):
        """Analyze variables in terms/expressions."""
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
        """
        Check if a variable is properly declared according to NAME-SCOPE-RULES.
        Implements the exact variable lookup rules from the specification.
        """
        # Apply the NAME-SCOPE-RULES for variable lookup
        if current_scope == ScopeType.LOCAL:
            if procedure_name:
                # IF this VAR's ALGO belongs to the Local scope of a Procedure
                if var_name in params:
                    # Variable is a parameter
                    self.update_symbol_table_for_var(var_name, ScopeType.LOCAL, is_parameter=True,
                                                   procedure_name=procedure_name)
                    return
                elif var_name in local_vars:
                    # Variable is locally declared
                    self.update_symbol_table_for_var(var_name, ScopeType.LOCAL, is_local=True,
                                                   procedure_name=procedure_name)
                    return
                elif var_name in self.global_variables:
                    # Variable is global
                    self.update_symbol_table_for_var(var_name, ScopeType.GLOBAL, is_global=True)
                    return
                else:
                    self.emit_undeclared_variable(var_name, f"procedure '{procedure_name}'")
                    
            elif function_name:
                # IF this VAR's ALGO belongs to the Local scope of a Function
                if var_name in params:
                    # Variable is a parameter
                    self.update_symbol_table_for_var(var_name, ScopeType.LOCAL, is_parameter=True,
                                                   function_name=function_name)
                    return
                elif var_name in local_vars:
                    # Variable is locally declared
                    self.update_symbol_table_for_var(var_name, ScopeType.LOCAL, is_local=True,
                                                   function_name=function_name)
                    return
                elif var_name in self.global_variables:
                    # Variable is global
                    self.update_symbol_table_for_var(var_name, ScopeType.GLOBAL, is_global=True)
                    return
                else:
                    self.emit_undeclared_variable(var_name, f"function '{function_name}'")
                    
        elif current_scope == ScopeType.MAIN:
            # IF this VAR's ALGO belongs to the Main scope
            if var_name in main_vars:
                # Variable is declared in main
                self.update_symbol_table_for_var(var_name, ScopeType.MAIN, is_main_var=True)
                return
            elif var_name in self.global_variables:
                # Variable is global
                self.update_symbol_table_for_var(var_name, ScopeType.GLOBAL, is_global=True)
                return
            else:
                self.emit_undeclared_variable(var_name, "main")
    
    def update_symbol_table_for_var(self, var_name: str, scope: ScopeType, 
                                   is_parameter: bool = False, is_local: bool = False,
                                   is_global: bool = False, is_main_var: bool = False,
                                   procedure_name: str = None, function_name: str = None):
        """
        Update the Symbol Table for a variable according to its determined scope.
        """
        # Create or update symbol entry
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
        """Emit a name-rule-violation notification."""
        self.st.add_error(f"NAME-RULE-VIOLATION: {message}")
    
    def emit_undeclared_variable(self, var_name: str, context: str):
        """Emit an undeclared-variable notification."""
        self.st.add_error(f"undeclared: UNDECLARED-VARIABLE: '{var_name}' in {context}")
    
    def print_symbol_table_report(self):
        """Print a detailed report of the symbol table for debugging."""
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
        # Check for duplicate parameters
        if len(proc.params) != len(set(proc.params)):
            self.st.add_error(f"Duplicate parameters in procedure {proc.name}")
            
        # Check for duplicate local variables
        if len(proc.local_vars) != len(set(proc.local_vars)):
            self.st.add_error(f"Duplicate local variables in procedure {proc.name}")
            
        # Check for shadowing
        param_set = set(proc.params)
        for local_var in proc.local_vars:
            if local_var in param_set:
                self.st.add_error(f"shadowing: Local variable '{local_var}' shadows parameter in procedure {proc.name}")
                
        # Analyze body
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
            
        # Check return atom
        if func.return_atom:
            self.check_variable_usage(func.return_atom, func.params, func.local_vars, ScopeType.LOCAL)
    
    def analyze_main(self, main: MainProgNode):
        # Check for duplicate variables in main
        if len(main.variables) != len(set(main.variables)):
            self.st.add_error("Duplicate variables in main program")
            
        # Check for conflicts with global variables
        main_vars = set(main.variables)
        conflicts = main_vars & self.st.global_vars
        if conflicts:
            self.st.add_warning(f"Main variables shadow global variables: {conflicts}")
            
        # Analyze main body
        if main.body:
            self.analyze_algo(main.body, [], main.variables, ScopeType.MAIN)
    
    def analyze_algo(self, algo: AlgoNode, params: List[str], local_vars: List[str], scope: ScopeType):
        for instr in algo.instructions:
            self.analyze_instruction(instr, params, local_vars, scope)
    
    def analyze_instruction(self, instr: InstrNode, params: List[str], local_vars: List[str], scope: ScopeType):
        if isinstance(instr, AssignNode):
            # Check if assigned variable is in scope
            if not self.is_variable_in_scope(instr.var, params, local_vars, scope):
                self.st.add_error(f"Variable '{instr.var}' not in scope for assignment")
            
            # Check expression
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
        # Check local scope first
        if var_name in params or var_name in local_vars:
            return True
        # Check global scope
        if var_name in self.st.global_vars:
            return True
        return False

# ============================================================================
# TYPE ANALYZER
# ============================================================================

class TypeAnalyzer:
    """
    COS341 Type Analyzer - Implements formal type analysis rules for SPL
    
    Following the semantic attribution rules exactly as specified:
    - Variables (VAR) are of type "numeric" (fact)
    - Numbers are of type "numeric" (fact)
    - Strings are correctly typed (fact)
    - Functions/procedures are type-less (have no type in Symbol Table)
    - Binary operators have specific type signatures
    - Unary operators have specific type signatures
    - Terms inherit types based on composition rules
    """
    
    def __init__(self, ast: ProgramNode, symbol_table: SymbolTable):
        self.ast = ast
        self.st = symbol_table
        
    def analyze(self) -> bool:
        """
        Main entry point for type analysis.
        Returns True if program is correctly typed, False otherwise.
        
        SPL_PROG is correctly typed if:
        - VARIABLES is correctly typed
        - PROCDEFS is correctly typed  
        - FUNCDEFS is correctly typed
        - MAINPROG is correctly typed
        """
        print("Phase 4: Type Analysis (COS341 Formal Rules)...")
        
        if not self.ast:
            self.st.add_error("AST is None - cannot perform type analysis")
            return False
            
        # Check global VARIABLES - they are all correctly typed (fact)
        variables_correct = self.check_variables(self.ast.variables)
        
        # Check PROCDEFS
        procdefs_correct = self.check_procdefs(self.ast.procedures)
        
        # Check FUNCDEFS  
        funcdefs_correct = self.check_funcdefs(self.ast.functions)
        
        # Check MAINPROG
        mainprog_correct = self.check_mainprog(self.ast.main)
        
        is_correctly_typed = (variables_correct and procdefs_correct and 
                            funcdefs_correct and mainprog_correct)
        
        if is_correctly_typed:
            print("✅ Type analysis passed - program is correctly typed")
        else:
            print("❌ Type analysis failed - program has type errors")
            
        return is_correctly_typed
    
    def check_variables(self, variables: List[str]) -> bool:
        """
        VARIABLES ::= // nothing, nullable
        VARIABLES ::= VAR VARIABLES
        
        Semantic Attribution:
        - Empty VARIABLES is correctly typed (fact)
        - VARIABLES is correctly typed if VAR is of type "numeric" 
          and VARIABLES (right-hand-side) is correctly typed
        """
        # All variables in SPL are of type "numeric" (fact)
        return True
    
    def check_procdefs(self, procedures: List[ProcDefNode]) -> bool:
        """
        PROCDEFS ::= // nothing, nullable
        PROCDEFS ::= PDEF PROCDEFS
        
        Semantic Attribution:
        - Empty PROCDEFS is correctly typed (fact)
        - PROCDEFS is correctly typed if PDEF is correctly typed
          and PROCDEFS (right-hand-side) is correctly typed
        """
        for proc in procedures:
            if not self.check_pdef(proc):
                return False
        return True
    
    def check_pdef(self, proc: ProcDefNode) -> bool:
        """
        PDEF ::= NAME ( PARAM ) { BODY }
        
        Semantic Attribution:
        PDEF is correctly typed if:
        - NAME is type-less (has no type in Symbol Table)
        - PARAM is correctly typed
        - BODY is correctly typed
        """
        # NAME (procedure name) should be type-less - this is handled by scope analysis
        
        # Check PARAM (parameters)
        param_correct = self.check_param(proc.params)
        
        # Check BODY
        body_correct = self.check_body(proc.local_vars, proc.body)
        
        if not (param_correct and body_correct):
            self.st.add_error(f"Procedure '{proc.name}' is not correctly typed")
            return False
            
        return True
    
    def check_funcdefs(self, functions: List[FuncDefNode]) -> bool:
        """
        FUNCDEFS ::= FDEF FUNCDEFS
        FUNCDEFS ::= // nothing, nullable
        
        Semantic Attribution:
        - Empty FUNCDEFS is correctly typed (fact)
        - FUNCDEFS is correctly typed if FDEF is correctly typed
          and FUNCDEFS (right-hand-side) is correctly typed
        """
        for func in functions:
            if not self.check_fdef(func):
                return False
        return True
    
    def check_fdef(self, func: FuncDefNode) -> bool:
        """
        FDEF ::= NAME ( PARAM ) { BODY ; return ATOM }
        
        Semantic Attribution:
        FDEF is correctly typed if:
        - NAME is type-less (has no type in Symbol Table)
        - PARAM is correctly typed
        - BODY is correctly typed
        - ATOM is of type "numeric"
        """
        # NAME (function name) should be type-less - handled by scope analysis
        
        # Check PARAM
        param_correct = self.check_param(func.params)
        
        # Check BODY
        body_correct = self.check_body(func.local_vars, func.body)
        
        # Check return ATOM is of type "numeric"
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
        """
        MAINPROG ::= var { VARIABLES } ALGO
        
        Semantic Attribution:
        MAINPROG is correctly typed if:
        - VARIABLES is correctly typed
        - ALGO is correctly typed
        """
        if not main:
            self.st.add_error("Main program is missing")
            return False
            
        # Check main VARIABLES
        variables_correct = self.check_variables(main.variables)
        
        # Check main ALGO
        algo_correct = self.check_algo(main.body)
        
        if not (variables_correct and algo_correct):
            self.st.add_error("Main program is not correctly typed")
            return False
            
        return True
    
    def check_body(self, local_vars: List[str], body: AlgoNode) -> bool:
        """
        BODY ::= local { MAXTHREE } ALGO
        
        Semantic Attribution:
        BODY is correctly typed if:
        - MAXTHREE is correctly typed 
        - ALGO is correctly typed
        """
        # Check MAXTHREE (local variables)
        maxthree_correct = self.check_maxthree(local_vars)
        
        # Check ALGO
        algo_correct = self.check_algo(body)
        
        return maxthree_correct and algo_correct
    
    def check_param(self, params: List[str]) -> bool:
        """
        PARAM ::= MAXTHREE
        
        Semantic Attribution:
        PARAM is correctly typed if MAXTHREE is correctly typed
        """
        return self.check_maxthree(params)
    
    def check_maxthree(self, vars_list: List[str]) -> bool:
        """
        MAXTHREE ::= // nothing, nullable
        MAXTHREE ::= VAR
        MAXTHREE ::= VAR VAR  
        MAXTHREE ::= VAR VAR VAR
        
        Semantic Attribution:
        - Empty MAXTHREE is correctly typed (fact)
        - MAXTHREE is correctly typed if all VAR are of type "numeric"
        """
        # All variables in SPL are of type "numeric" (fact)
        # Check that we don't exceed 3 variables
        if len(vars_list) > 3:
            self.st.add_error(f"Too many variables in MAXTHREE: {len(vars_list)} (max 3)")
            return False
        return True
    
    def check_algo(self, algo: AlgoNode) -> bool:
        """
        ALGO ::= INSTR
        ALGO ::= INSTR ; ALGO
        
        Semantic Attribution:
        - ALGO is correctly typed if INSTR is correctly typed
        - ALGO is correctly typed if INSTR is correctly typed 
          and ALGO (right-hand-side) is correctly typed
        """
        if not algo:
            return True
            
        for instr in algo.instructions:
            if not self.check_instr(instr):
                return False
        return True
    
    def check_instr(self, instr: InstrNode) -> bool:
        """
        Check instruction type correctness based on instruction type.
        """
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
        """
        INSTR ::= halt
        
        Semantic Attribution: INSTR is correctly typed (fact)
        """
        return True
    
    def check_print(self, print_node: PrintNode) -> bool:
        """
        INSTR ::= print OUTPUT
        
        Semantic Attribution: 
        INSTR is correctly typed if OUTPUT is correctly typed
        """
        return self.check_output(print_node.output, print_node.is_string)
    
    def check_call_instr(self, call: CallNode) -> bool:
        """
        INSTR ::= NAME ( INPUT )
        
        Semantic Attribution:
        INSTR is correctly typed if:
        - NAME is type-less (has no type in Symbol Table)
        - INPUT is correctly typed
        """
        # NAME should be type-less (procedure name)
        # This is verified during scope analysis
        
        # Check INPUT
        return self.check_input(call.args)
    
    def check_assign(self, assign: AssignNode) -> bool:
        """
        ASSIGN ::= VAR = NAME ( INPUT )
        ASSIGN ::= VAR = TERM
        
        Semantic Attribution:
        - For function call: correctly typed if NAME is type-less, 
          INPUT is correctly typed, and VAR is of type "numeric"
        - For term: correctly typed if TERM is of type "numeric"
          and VAR is of type "numeric"
        """
        # VAR is always of type "numeric" (fact)
        
        if assign.is_func_call and isinstance(assign.expr, CallNode):
            # Function call assignment
            call = assign.expr
            # NAME should be type-less (function name) - verified in scope analysis
            # Check INPUT
            return self.check_input(call.args)
        elif isinstance(assign.expr, TermNode):
            print(f"x is TermNode")
            # Term assignment
            term_type = self.get_term_type(assign.expr)
            if term_type != VarType.NUMERIC:
                print(f"Term type for '{assign.var}': {term_type}")
                self.st.add_error(f"Assignment to '{assign.var}': TERM is not of type 'numeric'")
                return False
            return True
        else:
            self.st.add_error(f"Invalid assignment expression type for '{assign.var}'")
            return False
    
    def check_loop(self, loop: LoopNode) -> bool:
        """
        LOOP ::= while TERM { ALGO }
        LOOP ::= do { ALGO } until TERM
        
        Semantic Attribution:
        LOOP is correctly typed if:
        - TERM is of type "boolean" or "numeric" (numeric allows implicit boolean conversion)
        - ALGO is correctly typed
        """
        if loop.condition:
            term_type = self.get_term_type(loop.condition)
            # if term_type not in [VarType.BOOLEAN, VarType.NUMERIC]: should only be boolean not numeric
            if term_type != VarType.BOOLEAN:
                self.st.add_error(f"Loop condition TERM must be 'boolean', got '{term_type.value}'")
                return False
        
        algo_correct = self.check_algo(loop.body)
        return algo_correct
    
    def check_branch(self, branch: BranchNode) -> bool:
        """
        BRANCH ::= if TERM { ALGO }
        BRANCH ::= if TERM { ALGO } else { ALGO }
        
        Semantic Attribution:
        BRANCH is correctly typed if:
        - TERM is of type "boolean" or "numeric" (numeric allows implicit boolean conversion)
        - Both ALGO are correctly typed
        """
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
        """
        OUTPUT ::= ATOM
        OUTPUT ::= string
        
        Semantic Attribution:
        - OUTPUT is correctly typed if ATOM is of type "numeric"
        - OUTPUT is correctly typed (fact) for string
        """
        if is_string:
            return True  # string is correctly typed (fact)
        else:
            # Must be ATOM
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
        """
        INPUT ::= // nothing, nullable
        INPUT ::= ATOM
        INPUT ::= ATOM ATOM
        INPUT ::= ATOM ATOM ATOM
        
        Semantic Attribution:
        - Empty INPUT is correctly typed (fact)
        - INPUT is correctly typed if all ATOM are of type "numeric"
        """
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
        """
        ATOM ::= VAR
        ATOM ::= number
        
        Semantic Attribution:
        - ATOM is of type "numeric" if VAR is of type "numeric"
        - ATOM is of type "numeric" (fact) for number
        """
        if not atom.is_var:
            # number
            return VarType.NUMERIC  # fact
        else:
            # VAR - all variables are of type "numeric" (fact)
            return VarType.NUMERIC
    
    def get_term_type(self, term: TermNode) -> VarType:
        # print(f"Getting type for TermNode: {term}")
        """
        Determine the type of a TERM based on composition rules.
        
        TERM ::= ATOM
        TERM ::= ( UNOP TERM )
        TERM ::= ( TERM BINOP TERM )
        """
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
        """
        TERM ::= ( UNOP TERM )
        
        Semantic Attribution:
        - TERM (left) is of type "numeric" if UNOP is "numeric" and TERM (right) is "numeric"
        - TERM (left) is of type "boolean" if UNOP is "boolean" and TERM (right) is "boolean" or "numeric"
        Note: 'not' operator can work with numeric operands (implicit boolean conversion)
        """
        operand_type = self.get_term_type(term.term)
        unop_type = self.get_unop_type(term.op)
        
        if unop_type == VarType.NUMERIC and operand_type == VarType.NUMERIC:
            return VarType.NUMERIC
        elif unop_type == VarType.BOOLEAN:
            # 'not' operator can work with boolean or numeric operands
            if operand_type in [VarType.BOOLEAN, VarType.NUMERIC]:
                return VarType.BOOLEAN
            else:
                self.st.add_error(f"UNOP '{term.op}' requires 'boolean' or 'numeric' operand, got '{operand_type.value}'")
                return VarType.TYPELESS
        else:
            self.st.add_error(f"UNOP '{term.op}' type mismatch: operator is {unop_type.value}, operand is {operand_type.value}")
            return VarType.TYPELESS
    
    def get_binop_term_type(self, term: BinopTermNode) -> VarType:
        """
        TERM ::= ( TERM BINOP TERM )
        
        Semantic Attribution:
        - TERM (left) is "numeric" if BINOP is "numeric" and both TERM (right) are "numeric"
        - TERM (left) is "boolean" if BINOP is "boolean" and both TERM (right) are "boolean"  
        - TERM (left) is "boolean" if BINOP is "comparison" and both TERM (right) are "numeric"
        """
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
            # Boolean operators (and, or) can work with boolean or numeric operands
            # if left_type in [VarType.BOOLEAN, VarType.NUMERIC] and right_type in [VarType.BOOLEAN, VarType.NUMERIC]:
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
        """
        UNOP ::= neg
        UNOP ::= not
        
        Semantic Attribution:
        - UNOP is of type "numeric" (fact) for neg
        - UNOP is of type "boolean" (fact) for not
        """
        if op == 'neg':
            return VarType.NUMERIC
        elif op == 'not':
            return VarType.BOOLEAN
        else:
            self.st.add_error(f"Unknown UNOP: {op}")
            return VarType.TYPELESS
    
    def get_binop_type(self, op: str) -> VarType:
        """
        BINOP type attribution (facts):
        - BINOP is of type "comparison" for > and eq
        - BINOP is of type "boolean" for or and and
        - BINOP is of type "numeric" for plus, minus, mult, div
        """
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
# CODE GENERATOR - Following COS341 Translation Rules
# ============================================================================

class CodeGenerator:
    def __init__(self, ast: ProgramNode, symbol_table: SymbolTable):
        self.ast = ast
        self.st = symbol_table
        self.code: List[str] = []
        self.temp_counter = 0
        self.label_counter = 0
        # Mapping from label name (e.g. L1, _L1, PROCname, start_label) to generated line numbers
        self.label_lineno: Dict[str, int] = {}
        # The final numbered output lines (strings with leading line numbers)
        self.numbered_code: List[str] = []
        
    def generate(self) -> List[str]:
        """
        Generate target code following COS341 translation rules.
        Variable declarations are NOT translated (only used for symbol table).
        Returns plain intermediate code WITHOUT line numbers.
        Line numbers will be added later after label processing.
        """
        if not self.ast:
            return []
            
        self.code = []
        
        print("Phase 5: Code Generation (COS341 Translation Rules)...")
        
        # Variable declarations are NOT translated - they were only for symbol table
        # Procedures and functions will be used for inlining (not implemented yet)
        
        # Generate main program (only the ALGO part)
        if self.ast.main:
            self.generate_main_algo(self.ast.main)

        # Return plain code without line numbers
        # Line numbering will be done AFTER label processing
        return self.code

    def number_instructions(self, increment: int = 10, start: int = 10) -> List[str]:
        """
        Assign line numbers to each instruction in self.code and return a
        new list of strings with the line number prefixed. Also populate
        self.label_lineno mapping for any label declarations found.

        Detection heuristics for label declarations:
        - Lines that start with 'REM <label>' (e.g. 'REM L1')
        - Lines that end with ':' (e.g. 'L1:' or 'start:')
        - 'PROC name:' and similar constructs will be captured by the colon rule
        """
        numbered: List[str] = []
        self.label_lineno = {}
        lineno = start

        for instr in self.code:
            # Trim-only for safe processing but preserve original spacing after number
            instr_str = instr.strip()

            # Detect labels declared via 'REM <label>'
            if instr_str.startswith('REM '):
                parts = instr_str.split()
                if len(parts) >= 2:
                    label = parts[1]
                    self.label_lineno[label] = lineno

            # Detect labels declared with trailing colon 'label:'
            if instr_str.endswith(':'):
                label = instr_str[:-1].strip()
                # For lines like 'PROC name:' map 'PROC name' as label name
                self.label_lineno[label] = lineno

            numbered.append(f"{lineno} {instr}")
            lineno += increment

        return numbered

    def get_label_mapping(self) -> Dict[str, int]:
        """Return the mapping from label names to their assigned line numbers."""
        return self.label_lineno
    
    def new_temp(self) -> str:
        """Generate a new temporary variable."""
        self.temp_counter += 1
        return f"t{self.temp_counter}"
    
    def new_label(self) -> str:
        """Generate a new label."""
        self.label_counter += 1
        return f"L{self.label_counter}"
    
    def emit(self, code: str):
        """Emit a line of target code."""
        self.code.append(code)
    
    def generate_main_algo(self, main: MainProgNode):
        """
        Translation: MAINPROG ::= var { VARIABLES } ALGO
        Only the ALGO gets translated, variable declarations are ignored.
        """
        if main.body:
            self.generate_algo(main.body)
    
    def generate_algo(self, algo: AlgoNode):
        """
        Translation: ALGO ::= INSTR ; ALGO
        Similar to Trans(Stat → Stat1 ; Stat2) from textbook Fig.6.5
        """
        for instr in algo.instructions:
            self.generate_instruction(instr)
    
    def generate_instruction(self, instr: InstrNode):
        """Generate code for a single instruction."""
        if isinstance(instr, HaltNode):
            self.generate_halt()
        elif isinstance(instr, PrintNode):
            self.generate_print(instr)
        elif isinstance(instr, AssignNode):
            self.generate_assign(instr)
        elif isinstance(instr, CallNode):
            self.generate_call(instr)
        elif isinstance(instr, BranchNode):
            self.generate_branch(instr)
        elif isinstance(instr, LoopNode):
            self.generate_loop(instr)
    
    def generate_halt(self):
        """
        Translation: INSTR ::= halt
        Trans(halt) = "STOP"
        """
        self.emit("STOP")
    
    def generate_print(self, print_instr: PrintNode):
        """
        Translation: INSTR ::= print OUTPUT
        
        Trans(print OUTPUT) = {
            if child_node(OUTPUT) == string then code = "string";
            if child_node(child_node(OUTPUT)) == number then code = "number";
            if child_node(child_node(OUTPUT)) == VAR then {
                internal = lookup_symbol_table(VAR);
                code = "internal";
            }
            target_code = "PRINT " ++ code;
        }
        """
        if print_instr.is_string:
            # String output
            self.emit(f"PRINT {print_instr.output}")
        else:
            # ATOM output (number or VAR)
            atom = print_instr.output
            if atom.is_var:
                # Variable - lookup in symbol table for internal name
                internal_name = self.lookup_internal_name(atom.value)
                self.emit(f"PRINT {internal_name}")
            else:
                # Number
                self.emit(f"PRINT {atom.value}")
    
    def generate_assign(self, assign: AssignNode):
        """
        Translation: ASSIGN ::= VAR = TERM
        Similar to Trans(Stat → id := Exp) from Fig.6.5, but using = instead of :=
        """
        if assign.is_func_call and isinstance(assign.expr, CallNode):
            # Function call assignment: VAR = NAME ( INPUT )
            # Generate CALL command (will be inlined later)
            temp = self.generate_function_call(assign.expr)
            var_internal = self.lookup_internal_name(assign.var)
            self.emit(f"{var_internal} = {temp}")
        else:
            # Regular assignment: VAR = TERM
            term_result = self.generate_term(assign.expr)
            var_internal = self.lookup_internal_name(assign.var)
            self.emit(f"{var_internal} = {term_result}")
    
    def generate_call(self, call: CallNode):
        """
        Translation: INSTR ::= NAME ( INPUT )  // procedure call without return
        Generate CALL command (will be replaced by inlining later)
        """
        args = []
        for arg in call.args:
            if arg.is_var:
                args.append(self.lookup_internal_name(arg.value))
            else:
                args.append(str(arg.value))
        
        args_str = ", ".join(args) if args else ""
        self.emit(f"CALL {call.name}({args_str})")
    
    def generate_function_call(self, call: CallNode) -> str:
        """Generate function call and return temporary variable holding result."""
        args = []
        for arg in call.args:
            if arg.is_var:
                args.append(self.lookup_internal_name(arg.value))
            else:
                args.append(str(arg.value))
        
        args_str = ", ".join(args) if args else ""
        temp = self.new_temp()
        self.emit(f"{temp} = CALL {call.name}({args_str})")
        return temp
    
    def generate_branch(self, branch: BranchNode):
        """
        Translation: BRANCH ::= if TERM { ALGO } [else { ALGO }]
        
        For if-else:
        IF t1 op t2 THEN labelT
        code_of_the_else_ALGO
        GOTO labelExit
        REM labelT
        code_of_the_then_ALGO
        REM labelExit
        
        For if-only:
        IF t1 op t2 THEN labelT
        GOTO labelExit
        REM labelT
        code_of_the_then_ALGO
        REM labelExit
        """
        label_t = self.new_label()
        label_exit = self.new_label()
        
        # Generate condition
        condition_code = self.generate_condition(branch.condition, label_t)
        self.emit(condition_code)
        
        if branch.else_branch:
            # if-else case
            self.generate_algo(branch.else_branch)
            self.emit(f"GOTO {label_exit}")
            self.emit(f"REM {label_t}")
            self.generate_algo(branch.then_branch)
            self.emit(f"REM {label_exit}")
        else:
            # if-only case
            self.emit(f"GOTO {label_exit}")
            self.emit(f"REM {label_t}")
            self.generate_algo(branch.then_branch)
            self.emit(f"REM {label_exit}")
    
    def generate_loop(self, loop: LoopNode):
        """
        Translation: LOOP ::= while TERM { ALGO } | do { ALGO } until TERM
        Similar to Figures 6.5 and 6.6, using REM instead of LABEL
        """
        if loop.is_while:
            # while TERM { ALGO }
            label_start = self.new_label()
            label_exit = self.new_label()
            label_body = self.new_label()
            
            self.emit(f"REM {label_start}")
            condition_code = self.generate_condition(loop.condition, label_body)
            self.emit(condition_code)
            self.emit(f"GOTO {label_exit}")
            self.emit(f"REM {label_body}")
            self.generate_algo(loop.body)
            self.emit(f"GOTO {label_start}")
            self.emit(f"REM {label_exit}")
        else:
            # do { ALGO } until TERM
            label_start = self.new_label()
            label_exit = self.new_label()
            
            self.emit(f"REM {label_start}")
            self.generate_algo(loop.body)
            # until condition - generate negated condition
            condition_code = self.generate_condition(loop.condition, label_exit)
            self.emit(condition_code)
            self.emit(f"GOTO {label_start}")
            self.emit(f"REM {label_exit}")
    
    def generate_condition(self, term: TermNode, true_label: str) -> str:
        """
        Generate condition code for branches and loops.
        Handles special cases like 'not' operator by swapping labels.
        """
        if isinstance(term, AtomTermNode):
            # Simple atom condition
            atom_code = self.generate_atom(term.atom)
            return f"IF {atom_code} THEN {true_label}"
            
        elif isinstance(term, UnopTermNode):
            if term.op == "not":
                # Special handling for 'not' - this will need label swapping at higher level
                inner_term_code = self.generate_term(term.term)
                return f"IF {inner_term_code} THEN {true_label}"
            elif term.op == "neg":
                inner_term_code = self.generate_term(term.term)
                temp = self.new_temp()
                self.emit(f"{temp} = -{inner_term_code}")
                return f"IF {temp} THEN {true_label}"
                
        elif isinstance(term, BinopTermNode):
            if term.op in ["eq", ">"]:
                # Comparison operators
                left_code = self.generate_term(term.left)
                right_code = self.generate_term(term.right)
                op_symbol = "=" if term.op == "eq" else ">"
                return f"IF {left_code} {op_symbol} {right_code} THEN {true_label}"
            else:
                # Other binary operations - evaluate to temp first
                term_result = self.generate_term(term)
                return f"IF {term_result} THEN {true_label}"
        
        # Default case
        term_result = self.generate_term(term)
        return f"IF {term_result} THEN {true_label}"
    
    def generate_term(self, term: TermNode) -> str:
        """
        Translation: TERM ::= ATOM | ( UNOP TERM ) | ( TERM BINOP TERM )
        Similar to Figure 6.3 in textbook, using = instead of :=
        """
        if isinstance(term, AtomTermNode):
            return self.generate_atom(term.atom)
            
        elif isinstance(term, UnopTermNode):
            operand = self.generate_term(term.term)
            temp = self.new_temp()
            if term.op == "neg":
                self.emit(f"{temp} = -{operand}")
            elif term.op == "not":
                # Handle 'not' specially since target language doesn't have boolean negation
                # This is complex and would need special handling in context
                self.emit(f"{temp} = NOT {operand}")  # Placeholder
            return temp
            
        elif isinstance(term, BinopTermNode):
            left = self.generate_term(term.left)
            right = self.generate_term(term.right)
            temp = self.new_temp()
            
            # Handle different binary operators
            if term.op == "plus":
                self.emit(f"{temp} = {left} + {right}")
            elif term.op == "minus":
                self.emit(f"{temp} = {left} - {right}")
            elif term.op == "mult":
                self.emit(f"{temp} = {left} * {right}")
            elif term.op == "div":
                self.emit(f"{temp} = {left} / {right}")
            elif term.op == "eq":
                self.emit(f"{temp} = {left} = {right}")
            elif term.op == ">":
                self.emit(f"{temp} = {left} > {right}")
            elif term.op in ["and", "or"]:
                # Boolean operators need cascading translation (Fig 6.8)
                # This is complex and would need special handling
                self.emit(f"{temp} = {left} {term.op.upper()} {right}")  # Placeholder
            
            return temp
        
        return "UNKNOWN_TERM"
    
    def generate_atom(self, atom: AtomNode) -> str:
        """
        Translation: ATOM ::= VAR | number
        Similar to Trans(Exp → id) and Trans(Exp → num) from Fig.6.3
        """
        if atom.is_var:
            return self.lookup_internal_name(atom.value)
        else:
            return str(atom.value)
    
    def lookup_internal_name(self, var_name: str) -> str:
        """
        Lookup variable in symbol table and return internal name.
        For now, return the original name (internal renaming not implemented).
        """
        # In a full implementation, this would lookup the symbol table
        # and return the internal renamed variable
        return var_name
    
    def emit(self, instruction: str):
        self.code.append(instruction)
    
    def generate_procedure(self, proc: ProcDefNode):
        self.emit(f"PROC {proc.name}:")
        
        # Declare parameters
        for param in proc.params:
            self.emit(f"  PARAM {param}")
        
        # Declare local variables
        for local_var in proc.local_vars:
            self.emit(f"  LOCAL {local_var}")
        
        # Generate body
        if proc.body:
            self.generate_algo(proc.body, "  ")
        
        self.emit(f"  RETURN")
        self.emit(f"ENDPROC {proc.name}")
    
    def generate_function(self, func: FuncDefNode):
        self.emit(f"FUNC {func.name}:")
        
        # Declare parameters
        for param in func.params:
            self.emit(f"  PARAM {param}")
        
        # Declare local variables
        for local_var in func.local_vars:
            self.emit(f"  LOCAL {local_var}")
        
        # Generate body
        if func.body:
            self.generate_algo(func.body, "  ")
        
        # Generate return statement
        if func.return_atom:
            if func.return_atom.is_var:
                self.emit(f"  RETURN {func.return_atom.value}")
            else:
                self.emit(f"  RETURN {func.return_atom.value}")
        
        self.emit(f"ENDFUNC {func.name}")
    
    def generate_main(self, main: MainProgNode):
        self.emit("MAIN:")
        
        # Declare main variables
        for var in main.variables:
            self.emit(f"  LOCAL {var}")
        
        # Generate body
        if main.body:
            self.generate_algo(main.body, "  ")
        
        self.emit("ENDMAIN")
    
    def generate_algo(self, algo: AlgoNode, indent: str = ""):
        for instr in algo.instructions:
            self.generate_instruction(instr, indent)
    
    def generate_instruction(self, instr: InstrNode, indent: str = ""):
        if isinstance(instr, HaltNode):
            self.emit(f"{indent}HALT")
            
        elif isinstance(instr, PrintNode):
            if instr.is_string:
                self.emit(f"{indent}PRINT {instr.output}")
            else:
                if instr.output.is_var:
                    self.emit(f"{indent}PRINT {instr.output.value}")
                else:
                    self.emit(f"{indent}PRINT {instr.output.value}")
                    
        elif isinstance(instr, AssignNode):
            if instr.is_func_call and isinstance(instr.expr, CallNode):
                # Function call assignment
                call = instr.expr
                args_str = ", ".join([self.get_atom_value(arg) for arg in call.args])
                self.emit(f"{indent}{instr.var} = CALL {call.name}({args_str})")
            elif isinstance(instr.expr, TermNode):
                # Expression assignment
                temp = self.generate_term(instr.expr, indent)
                self.emit(f"{indent}{instr.var} = {temp}")
                
        elif isinstance(instr, CallNode):
            # Procedure call
            args_str = ", ".join([self.get_atom_value(arg) for arg in instr.args])
            self.emit(f"{indent}CALL {instr.name}({args_str})")
            
        elif isinstance(instr, BranchNode):
            if instr.condition:
                cond_temp = self.generate_term(instr.condition, indent)
                else_label = self.st.new_label()
                end_label = self.st.new_label()
                
                self.emit(f"{indent}IF NOT {cond_temp} GOTO {else_label}")
                
                if instr.then_branch:
                    self.generate_algo(instr.then_branch, indent)
                
                if instr.else_branch:
                    self.emit(f"{indent}GOTO {end_label}")
                    self.emit(f"{else_label}:")
                    self.generate_algo(instr.else_branch, indent)
                    self.emit(f"{end_label}:")
                else:
                    self.emit(f"{else_label}:")
                    
        elif isinstance(instr, LoopNode):
            if instr.is_while:
                start_label = self.st.new_label()
                end_label = self.st.new_label()
                
                self.emit(f"{start_label}:")
                if instr.condition:
                    cond_temp = self.generate_term(instr.condition, indent)
                    self.emit(f"{indent}IF NOT {cond_temp} GOTO {end_label}")
                
                if instr.body:
                    self.generate_algo(instr.body, indent)
                
                self.emit(f"{indent}GOTO {start_label}")
                self.emit(f"{end_label}:")
            else:
                # do-until loop
                start_label = self.st.new_label()
                
                self.emit(f"{start_label}:")
                if instr.body:
                    self.generate_algo(instr.body, indent)
                
                if instr.condition:
                    cond_temp = self.generate_term(instr.condition, indent)
                    self.emit(f"{indent}IF NOT {cond_temp} GOTO {start_label}")
    
    def generate_term(self, term: TermNode, indent: str = "") -> str:
        if isinstance(term, AtomTermNode):
            return self.get_atom_value(term.atom)
            
        elif isinstance(term, UnopTermNode):
            operand = self.generate_term(term.term, indent)
            temp = self.st.new_temp()
            self.emit(f"{indent}{temp} = {term.op.upper()} {operand}")
            return temp
            
        elif isinstance(term, BinopTermNode):
            left = self.generate_term(term.left, indent)
            right = self.generate_term(term.right, indent)
            temp = self.st.new_temp()
            
            op_map = {
                'plus': '+', 'minus': '-', 'mult': '*', 'div': '/',
                'eq': '==', '>': '>', 'and': '&&', 'or': '||'
            }
            op = op_map.get(term.op, term.op.upper())
            self.emit(f"{indent}{temp} = {left} {op} {right}")
            return temp
        
        return "UNKNOWN"
    
    def get_atom_value(self, atom: AtomNode) -> str:
        if atom.is_var:
            return atom.value
        else:
            return str(atom.value)


# ============================================================================
# MAIN COMPILER
# ============================================================================

def compile_spl_with_antlr(source_code: str, output_file: str = None) -> bool:
    """SPL compilation using ANTLR parser"""
    if not ANTLR_AVAILABLE:
        print("ANTLR not available! Falling back to hand-written parser.")
        return compile_spl(source_code, output_file)
    
    try:
        # Phase 1 & 2: ANTLR Lexing and Parsing
        print("Phase 1-2: ANTLR Lexical and Syntax Analysis...")
        input_stream = InputStream(source_code)
        lexer = SPLLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = SPLParser(stream)
        
        tree = parser.spl_prog()
        
        # Convert ANTLR parse tree to our AST
        symbol_table = SymbolTable()
        visitor = SPLASTVisitor(symbol_table)
        ast = visitor.visit(tree)
        
        # Continue with our analysis phases
        return continue_compilation(ast, symbol_table, output_file)
        
    except Exception as e:
        print(f"ANTLR parsing failed: {e}")
        return False

# ============================================================================
# LABEL AND JUMP PROCESSING
# ============================================================================

def process_labels_and_jumps(intermediate_code: List[str]) -> Tuple[List[str], Dict[str, int]]:
    """
    Process labels and jumps in intermediate code.
    
    This function:
    1. Scans through the intermediate code to find all label definitions
    2. Creates a mapping of label names to their line numbers
    3. Replaces all GOTO label references with GOTO line_number
    4. Replaces all THEN label references with THEN line_number
    5. Converts label definitions to REM statements
    
    Args:
        intermediate_code: List of intermediate code lines (may contain labels)
    
    Returns:
        Tuple of (final_code, label_map) where:
        - final_code is the code with resolved jumps
        - label_map is a dictionary mapping label names to line numbers
    
    Examples:
        Input:
            _L1:
            x = 10
            IF x > 5 THEN _L1
            GOTO _L1
        
        Output:
            REM _L1
            x = 10
            IF x > 5 THEN 1
            GOTO 1
            
        Label Map: {'_L1': 1}
    """
    # Phase 1: Build label map by scanning code
    label_map: Dict[str, int] = {}
    cleaned_code: List[str] = []
    
    # First pass: identify labels and build mapping
    line_number = 1
    for code_line in intermediate_code:
        stripped = code_line.strip()
        
        # Check if this line is a label definition (ends with :)
        if stripped.endswith(':'):
            # Extract label name (remove the colon)
            label_name = stripped[:-1].strip()
            # Map label to current line number
            label_map[label_name] = line_number
            # Convert label to REM statement for documentation
            cleaned_code.append(f"REM {label_name}")
            line_number += 1
        elif stripped.startswith('REM '):
            # Already a REM statement, keep it
            cleaned_code.append(code_line)
            line_number += 1
        elif stripped:  # Non-empty line
            cleaned_code.append(code_line)
            line_number += 1
        # Skip completely empty lines
    
    # Phase 2: Replace label references with line numbers
    final_code: List[str] = []
    
    for code_line in cleaned_code:
        modified_line = code_line
        
        # Replace GOTO label references
        if 'GOTO ' in modified_line:
            parts = modified_line.split('GOTO ')
            if len(parts) > 1:
                # Extract the label (everything after GOTO until whitespace or end of line)
                after_goto = parts[1].strip()
                # Split on whitespace to get just the label
                label_parts = after_goto.split()
                if label_parts:
                    potential_label = label_parts[0]
                    # Check if this is a label we know about
                    if potential_label in label_map:
                        target_line = label_map[potential_label]
                        # Replace the label with the line number
                        modified_line = modified_line.replace(
                            f'GOTO {potential_label}',
                            f'GOTO {target_line}'
                        )
        
        # Replace THEN label references
        if 'THEN ' in modified_line:
            parts = modified_line.split('THEN ')
            if len(parts) > 1:
                # Extract the label after THEN
                after_then = parts[1].strip()
                # Split on whitespace to get just the label
                label_parts = after_then.split()
                if label_parts:
                    potential_label = label_parts[0]
                    # Check if this is a label we know about
                    if potential_label in label_map:
                        target_line = label_map[potential_label]
                        # Replace the label with the line number
                        modified_line = modified_line.replace(
                            f'THEN {potential_label}',
                            f'THEN {target_line}'
                        )
        
        final_code.append(modified_line)
    
    return final_code, label_map

def compile_spl(source_code: str, output_file: str = None) -> bool:
    """Complete SPL compilation pipeline with hand-written parser"""
    
    # Phase 1: Lexical Analysis
    print("Phase 1: Lexical Analysis...")
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    
    # Phase 2: Syntax Analysis (Parsing)
    print("Phase 2: Syntax Analysis...")
    symbol_table = SymbolTable()
    parser = Parser(tokens, symbol_table)
    ast = parser.parse()
    
    if symbol_table.has_errors():
        print("Parsing failed!")
        symbol_table.print_report()
        return False
    
    return continue_compilation(ast, symbol_table, output_file)

def continue_compilation(ast: ProgramNode, symbol_table: SymbolTable, output_file: str = None) -> bool:
    """Continue compilation from AST through remaining phases"""
    
    # Phase 3: NAME-SCOPE-RULES Analysis
    print("Phase 3: NAME-SCOPE-RULES Analysis...")
    scope_analyzer = ScopeAnalyzer(ast, symbol_table)
    scope_analyzer.analyze()
    
    # Print detailed symbol table report
    scope_analyzer.print_symbol_table_report()
    
    if symbol_table.has_errors():
        print("NAME-SCOPE-RULES analysis failed!")
        symbol_table.print_report()
        return False
    
    # Phase 4: Type Analysis
    type_analyzer = TypeAnalyzer(ast, symbol_table)
    is_correctly_typed = type_analyzer.analyze()
    
    if not is_correctly_typed or symbol_table.has_errors():
        print("Type analysis failed!")
        symbol_table.print_report()
        return False
    
    # Phase 5: Code Generation (COS341 Translation Rules)
    print("Phase 5: Code Generation...")
    code_generator = CodeGenerator(ast, symbol_table)
    intermediate_code = code_generator.generate()
    
    # Output results
    symbol_table.print_report()
    
    print("\n=== INTERMEDIATE CODE (Before Label Processing) ===")
    for i, line in enumerate(intermediate_code, 1):
        print(f"{i:4d}: {line}")
    
    # Phase 6: Process Labels and Jumps
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
            # Write with line numbers for BASIC format (multiples of 10)
            for i, line in enumerate(final_code, 1):
                if line.strip():  # Only write non-empty lines
                    f.write(f"{i * 10} {line}\n")
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