#!/usr/bin/env python3
"""
Test script to demonstrate line numbering and label mapping functionality
"""

import sys
sys.path.insert(0, '.')

from compiler import Lexer, Parser, SymbolTable, ScopeAnalyzer, TypeAnalyzer, CodeGenerator

def test_label_mapping(source_code: str, description: str):
    print(f"\n{'='*70}")
    print(f"Test: {description}")
    print(f"{'='*70}")
    
    # Compile
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    
    symbol_table = SymbolTable()
    parser = Parser(tokens, symbol_table)
    ast = parser.parse()
    
    if symbol_table.has_errors():
        print("❌ Parsing failed!")
        symbol_table.print_report()
        return
    
    scope_analyzer = ScopeAnalyzer(ast, symbol_table)
    scope_analyzer.analyze()
    
    if symbol_table.has_errors():
        print("❌ Scope analysis failed!")
        symbol_table.print_report()
        return
    
    type_analyzer = TypeAnalyzer(ast, symbol_table)
    is_correctly_typed = type_analyzer.analyze()
    
    if not is_correctly_typed or symbol_table.has_errors():
        print("❌ Type analysis failed!")
        symbol_table.print_report()
        return
    
    # Generate code
    code_generator = CodeGenerator(ast, symbol_table)
    numbered_code = code_generator.generate()
    label_mapping = code_generator.get_label_mapping()
    
    print("\n✅ Compilation successful!")
    print(f"\n📝 Generated Code ({len(numbered_code)} instructions):")
    print("-" * 70)
    for line in numbered_code:
        print(line)
    
    print(f"\n🏷️  Label Mapping ({len(label_mapping)} labels):")
    print("-" * 70)
    if label_mapping:
        for label, line_num in sorted(label_mapping.items(), key=lambda x: x[1]):
            print(f"  {label:20} -> Line {line_num}")
    else:
        print("  (No labels found)")
    print()

# Test 1: Simple program with no labels
test1 = """
glob { }
proc { }
func { }
main {
    var { x y }
    x = 5;
    y = 10;
    print x;
    print y;
    halt
}
"""

# Test 2: Program with if-else (has labels)
test2 = """
glob { }
proc { }
func { }
main {
    var { a b }
    a = 10;
    b = 5;
    if (> a b) {
        print "a is greater"
    } else {
        print "b is greater or equal"
    };
    halt
}
"""

# Test 3: Program with loop (has labels)
test3 = """
glob { }
proc { }
func { }
main {
    var { count }
    count = 0;
    do {
        print count;
        count = (plus count 1)
    } until (eq count 5);
    halt
}
"""

# Test 4: Program with while loop (has labels)
test4 = """
glob { }
proc { }
func { }
main {
    var { i }
    i = 0;
    while (> 3 i) {
        print i;
        i = (plus i 1)
    };
    halt
}
"""

if __name__ == "__main__":
    test_label_mapping(test1, "Simple program (no branches/loops)")
    test_label_mapping(test2, "Program with if-else branches")
    test_label_mapping(test3, "Program with do-until loop")
    test_label_mapping(test4, "Program with while loop")
    
    print(f"\n{'='*70}")
    print("✨ All tests completed!")
    print(f"{'='*70}\n")
