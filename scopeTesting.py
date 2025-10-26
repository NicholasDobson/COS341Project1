"""
SPL Compiler - Comprehensive Scope Testing
Tests all scope-related rules and edge cases with 100% coverage

Tests:
1. Global scope variable declarations
2. Procedure scope with parameters and local variables
3. Function scope with parameters and local variables
4. Main scope variable declarations
5. Variable shadowing (should fail)
6. Double declarations in same scope (should fail)
7. Cross-scope variable access
8. Undeclared variable errors
9. Name conflicts (variable/function/procedure)
10. Parameter shadowing by local variables (should fail)
11. Edge cases with empty scopes
12. Multiple levels of nesting
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from compiler import (
    compile_spl, SymbolTable, ScopeType, VarType,
    Lexer, Parser, ScopeAnalyzer, ProgramNode
)


class ScopeTestRunner:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def run_test(self, test_name: str, spl_code: str, should_pass: bool, 
                 expected_errors: list = None, check_symbols: dict = None):
        """
        Run a single scope test.
        
        Args:
            test_name: Name of the test
            spl_code: SPL source code to test
            should_pass: True if test should pass, False if should fail
            expected_errors: List of expected error substrings (for failing tests)
            check_symbols: Dict of symbol checks {var_name: expected_scope_type}
        """
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")
        print("SPL Code:")
        print(spl_code)
        print("-" * 70)
        
        try:
            # Phase 1: Lexical Analysis
            lexer = Lexer(spl_code)
            tokens = lexer.tokenize()
            
            # Phase 2: Syntax Analysis
            symbol_table = SymbolTable()
            parser = Parser(tokens, symbol_table)
            ast = parser.parse()
            
            if symbol_table.has_errors():
                print("Parsing failed!")
                symbol_table.print_report()
                success = False
            else:
                # Phase 3: Scope Analysis
                scope_analyzer = ScopeAnalyzer(ast, symbol_table)
                scope_analyzer.analyze()
                
                # Check if errors exist
                has_errors = symbol_table.has_errors()
                success = not has_errors if should_pass else has_errors
                
                # Print symbol table report
                scope_analyzer.print_symbol_table_report()
                symbol_table.print_report()
                
                # Check expected errors
                if expected_errors and has_errors:
                    all_errors = ' '.join(symbol_table.errors)
                    for expected_err in expected_errors:
                        if expected_err.lower() not in all_errors.lower():
                            print(f"ERROR: Expected error containing '{expected_err}' not found!")
                            success = False
                
                # Check symbol properties
                if check_symbols and success and should_pass:
                    for var_name, expected_scope in check_symbols.items():
                        symbols = symbol_table.var_lookup.get(var_name, [])
                        if not symbols:
                            print(f"ERROR: Symbol '{var_name}' not found in symbol table!")
                            success = False
                        else:
                            found = False
                            for sym in symbols:
                                if sym.scope == expected_scope:
                                    found = True
                                    print(f"✓ Symbol '{var_name}' has expected scope: {expected_scope}")
                                    break
                            if not found:
                                print(f"ERROR: Symbol '{var_name}' does not have expected scope {expected_scope}")
                                print(f"  Found scopes: {[s.scope for s in symbols]}")
                                success = False
            
            # Test result
            if success:
                print(f"\n✅ TEST PASSED: {test_name}")
                self.tests_passed += 1
                self.test_results.append((test_name, "PASSED"))
            else:
                print(f"\n❌ TEST FAILED: {test_name}")
                self.tests_failed += 1
                self.test_results.append((test_name, "FAILED"))
                
        except Exception as e:
            print(f"\n❌ TEST FAILED WITH EXCEPTION: {test_name}")
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            self.test_results.append((test_name, "EXCEPTION"))
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        for test_name, result in self.test_results:
            symbol = "✅" if result == "PASSED" else "❌"
            print(f"{symbol} {test_name}: {result}")
        
        print("-"*70)
        total = self.tests_passed + self.tests_failed
        print(f"Total Tests: {total}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/total*100) if total > 0 else 0:.1f}%")
        print("="*70)


def main():
    runner = ScopeTestRunner()
    
    # ========================================================================
    # TEST 1: Simple Global Variables
    # ========================================================================
    runner.run_test(
        "TEST 1: Simple Global Variables",
        """
        glob {
            x
            y
            z
        }
        proc {}
        func {}
        main {
            var {}
            x = 5
        }
        """,
        should_pass=True,
        check_symbols={
            'x': ScopeType.GLOBAL,
            'y': ScopeType.GLOBAL,
            'z': ScopeType.GLOBAL
        }
    )
    
    # ========================================================================
    # TEST 2: Global Variable Double Declaration (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 2: Global Variable Double Declaration",
        """
        glob {
            x
            y
            x
        }
        proc {}
        func {}
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["double-declaration", "name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 3: Procedure with Parameters
    # ========================================================================
    runner.run_test(
        "TEST 3: Procedure with Parameters",
        """
        glob {}
        proc {
            myproc(a b c) {
                local {}
                print a
            }
        }
        func {}
        main {
            var {}
            myproc(1 2 3)
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 4: Procedure with Local Variables
    # ========================================================================
    runner.run_test(
        "TEST 4: Procedure with Local Variables",
        """
        glob {}
        proc {
            myproc(a) {
                local {
                    temp
                    result
                }
                temp = (a plus 1);
                print temp
            }
        }
        func {}
        main {
            var {}
            myproc(5)
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 5: Parameter Shadowing by Local Variable (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 5: Parameter Shadowing by Local Variable",
        """
        glob {}
        proc {
            myproc(a b) {
                local {
                    a
                    temp
                }
                print a
            }
        }
        func {}
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["shadowing", "name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 6: Function with Return
    # ========================================================================
    runner.run_test(
        "TEST 6: Function with Return",
        """
        glob {}
        proc {}
        func {
            compute(x y) {
                local {
                    result
                }
                result = (x plus y);
                return result
            }
        }
        main {
            var {
                answer
            }
            answer = compute(5 10)
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 7: Function Parameter Shadowing (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 7: Function Parameter Shadowing",
        """
        glob {}
        proc {}
        func {
            compute(x y) {
                local {
                    x
                }
                return x
            }
        }
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["shadowing", "name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 8: Main Local Variables
    # ========================================================================
    runner.run_test(
        "TEST 8: Main Local Variables",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                x
                y
                z
            }
            x = 10;
            y = 20;
            z = (x plus y);
            print z
        }
        """,
        should_pass=True,
        check_symbols={
            'x': ScopeType.MAIN,
            'y': ScopeType.MAIN,
            'z': ScopeType.MAIN
        }
    )
    
    # ========================================================================
    # TEST 9: Main Variable Double Declaration (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 9: Main Variable Double Declaration",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                x
                y
                x
            }
            halt
        }
        """,
        should_pass=False,
        expected_errors=["double-declaration", "name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 10: Undeclared Variable in Main (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 10: Undeclared Variable in Main",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                x
            }
            y = 10
        }
        """,
        should_pass=False,
        expected_errors=["undeclared"]
    )
    
    # ========================================================================
    # TEST 11: Global Variable Access from Main
    # ========================================================================
    runner.run_test(
        "TEST 11: Global Variable Access from Main",
        """
        glob {
            globalvar
        }
        proc {}
        func {}
        main {
            var {
                localvar
            }
            globalvar = 100;
            localvar = (globalvar plus 50);
            print localvar
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 12: Global Variable Access from Procedure
    # ========================================================================
    runner.run_test(
        "TEST 12: Global Variable Access from Procedure",
        """
        glob {
            counter
        }
        proc {
            increment() {
                local {}
                counter = (counter plus 1)
            }
        }
        func {}
        main {
            var {}
            counter = 0;
            increment();
            print counter
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 13: Global Variable Access from Function
    # ========================================================================
    runner.run_test(
        "TEST 13: Global Variable Access from Function",
        """
        glob {
            base
        }
        proc {}
        func {
            addtobase(x) {
                local {
                    result
                }
                result = (base plus x);
                return result
            }
        }
        main {
            var {
                answer
            }
            base = 100;
            answer = addtobase(50);
            print answer
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 14: Undeclared Variable in Procedure (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 14: Undeclared Variable in Procedure",
        """
        glob {}
        proc {
            myproc() {
                local {
                    x
                }
                y = 10
            }
        }
        func {}
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["undeclared"]
    )
    
    # ========================================================================
    # TEST 15: Undeclared Variable in Function (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 15: Undeclared Variable in Function",
        """
        glob {}
        proc {}
        func {
            myfunc() {
                local {
                    x
                }
                y = 10;
                return y
            }
        }
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["undeclared"]
    )
    
    # ========================================================================
    # TEST 16: Variable Name Same as Procedure Name (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 16: Variable Name Same as Procedure Name",
        """
        glob {
            myproc
        }
        proc {
            myproc() {
                local {}
                halt
            }
        }
        func {}
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 17: Variable Name Same as Function Name (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 17: Variable Name Same as Function Name",
        """
        glob {
            myfunc
        }
        proc {}
        func {
            myfunc() {
                local {}
                return 0
            }
        }
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 18: Function Name Same as Procedure Name (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 18: Function Name Same as Procedure Name",
        """
        glob {}
        proc {
            duplicate() {
                local {}
                halt
            }
        }
        func {
            duplicate() {
                local {}
                return 0
            }
        }
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 19: Multiple Procedures with Different Names
    # ========================================================================
    runner.run_test(
        "TEST 19: Multiple Procedures with Different Names",
        """
        glob {}
        proc {
            proc1() {
                local {}
                halt
            }
            proc2() {
                local {}
                halt
            }
            proc3() {
                local {}
                halt
            }
        }
        func {}
        main {
            var {}
            proc1();
            proc2();
            proc3()
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 20: Duplicate Procedure Names (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 20: Duplicate Procedure Names",
        """
        glob {}
        proc {
            proc1() {
                local {}
                halt
            }
            proc1() {
                local {}
                halt
            }
        }
        func {}
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["double-declaration", "name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 21: Multiple Functions with Different Names
    # ========================================================================
    runner.run_test(
        "TEST 21: Multiple Functions with Different Names",
        """
        glob {}
        proc {}
        func {
            func1() {
                local {}
                return 1
            }
            func2() {
                local {}
                return 2
            }
        }
        main {
            var {
                a
                b
            }
            a = func1();
            b = func2()
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 22: Duplicate Function Names (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 22: Duplicate Function Names",
        """
        glob {}
        proc {}
        func {
            func1() {
                local {}
                return 1
            }
            func1() {
                local {}
                return 2
            }
        }
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["double-declaration", "name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 23: Procedure Parameter Double Declaration (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 23: Procedure Parameter Double Declaration",
        """
        glob {}
        proc {
            myproc(a b a) {
                local {}
                halt
            }
        }
        func {}
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["double-declaration", "name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 24: Function Parameter Double Declaration (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 24: Function Parameter Double Declaration",
        """
        glob {}
        proc {}
        func {
            myfunc(x y x) {
                local {}
                return 0
            }
        }
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["double-declaration", "name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 25: Procedure Local Variable Double Declaration (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 25: Procedure Local Variable Double Declaration",
        """
        glob {}
        proc {
            myproc() {
                local {
                    temp
                    result
                    temp
                }
                halt
            }
        }
        func {}
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["double-declaration", "name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 26: Function Local Variable Double Declaration (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 26: Function Local Variable Double Declaration",
        """
        glob {}
        proc {}
        func {
            myfunc() {
                local {
                    temp
                    result
                    temp
                }
                return 0
            }
        }
        main {
            var {}
            halt
        }
        """,
        should_pass=False,
        expected_errors=["double-declaration", "name-rule-violation"]
    )
    
    # ========================================================================
    # TEST 27: Complex Scope Hierarchy
    # ========================================================================
    runner.run_test(
        "TEST 27: Complex Scope Hierarchy",
        """
        glob {
            globalx
            globaly
        }
        proc {
            proca(parama) {
                local {
                    locala
                }
                locala = (parama plus globalx);
                globaly = locala
            }
        }
        func {
            funcb(paramb) {
                local {
                    localb
                }
                localb = (paramb mult globalx);
                return localb
            }
        }
        main {
            var {
                mainx
                mainy
            }
            globalx = 10;
            globaly = 20;
            mainx = 5;
            proca(mainx);
            mainy = funcb(mainx);
            print mainy
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 28: Empty Scopes
    # ========================================================================
    runner.run_test(
        "TEST 28: Empty Scopes",
        """
        glob {}
        proc {}
        func {}
        main {
            var {}
            halt
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 29: Same Variable Name in Different Local Scopes (Should Pass)
    # ========================================================================
    runner.run_test(
        "TEST 29: Same Variable Name in Different Local Scopes",
        """
        glob {}
        proc {
            proc1() {
                local {
                    temp
                }
                temp = 10
            }
            proc2() {
                local {
                    temp
                }
                temp = 20
            }
        }
        func {}
        main {
            var {}
            proc1();
            proc2()
        }
        """,
        should_pass=True
    )
    
    # ========================================================================
    # TEST 30: Procedure Calling Undeclared Procedure (Should Fail)
    # ========================================================================
    runner.run_test(
        "TEST 30: Undeclared Procedure Call",
        """
        glob {}
        proc {}
        func {}
        main {
            var {}
            undeclaredproc()
        }
        """,
        should_pass=False,
        expected_errors=["undeclared"]
    )
    
    runner.print_summary()
    
    return 0 if runner.tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())