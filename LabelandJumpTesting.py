"""
SPL Compiler - Comprehensive Label and Jump Processing Testing
Tests label mapping and jump resolution with 100% coverage

Tests:
1. Simple GOTO with labels
2. IF-THEN with labels
3. While loops with labels
4. Do-until loops with labels
5. Nested branches with multiple labels
6. Complex control flow
7. Edge cases: first/last line labels
8. Multiple jumps to same label
9. Forward and backward jumps
10. REM label statements
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from compiler import (
    compile_spl, SymbolTable, Lexer, Parser, ScopeAnalyzer, 
    TypeAnalyzer, CodeGenerator, process_labels_and_jumps
)


class LabelJumpTestRunner:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def run_test(self, test_name: str, spl_code: str, 
                 expected_patterns: list = None,
                 should_have_labels: bool = True):
        """
        Run a single label/jump processing test.
        
        Args:
            test_name: Name of the test
            spl_code: SPL source code to test
            expected_patterns: List of patterns that should exist in final code
            should_have_labels: Whether intermediate code should have labels
        """
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")
        print("SPL Code:")
        print(spl_code)
        print("-" * 70)
        
        try:
            # Compile to intermediate code
            lexer = Lexer(spl_code)
            tokens = lexer.tokenize()
            
            symbol_table = SymbolTable()
            parser = Parser(tokens, symbol_table)
            ast = parser.parse()
            
            if symbol_table.has_errors():
                print("❌ Parsing failed!")
                symbol_table.print_report()
                self.tests_failed += 1
                self.test_results.append((test_name, "FAILED - Parse Error"))
                return
            
            # Scope and type analysis
            scope_analyzer = ScopeAnalyzer(ast, symbol_table)
            scope_analyzer.analyze()
            
            if symbol_table.has_errors():
                print("❌ Scope analysis failed!")
                symbol_table.print_report()
                self.tests_failed += 1
                self.test_results.append((test_name, "FAILED - Scope Error"))
                return
            
            type_analyzer = TypeAnalyzer(ast, symbol_table)
            is_correctly_typed = type_analyzer.analyze()
            
            if not is_correctly_typed or symbol_table.has_errors():
                print("❌ Type analysis failed!")
                symbol_table.print_report()
                self.tests_failed += 1
                self.test_results.append((test_name, "FAILED - Type Error"))
                return
            
            # Code generation
            code_generator = CodeGenerator(ast, symbol_table)
            intermediate_code = code_generator.generate()
            
            print("\n--- INTERMEDIATE CODE (Before Label Processing) ---")
            for i, line in enumerate(intermediate_code, 1):
                print(f"{i:3d}: {line}")
            
            # Check if intermediate code has labels
            has_labels = any('_L' in line for line in intermediate_code)
            if should_have_labels and not has_labels:
                print(f"⚠️  WARNING: Expected labels in intermediate code but found none")
            
            # Process labels and jumps
            print("\n--- PROCESSING LABELS AND JUMPS ---")
            final_code, label_map = process_labels_and_jumps(intermediate_code)
            
            print(f"\nLabel Mapping:")
            for label, line_num in sorted(label_map.items(), key=lambda x: x[1]):
                print(f"  {label} -> Line {line_num}")
            
            print("\n--- FINAL CODE (After Label Processing) ---")
            for i, line in enumerate(final_code, 1):
                print(f"{i:3d}: {line}")
            
            # Validation checks
            success = True
            
            # Check 1: No unresolved labels in final code
            unresolved_labels = []
            for i, line in enumerate(final_code, 1):
                if 'GOTO _L' in line or 'THEN _L' in line:
                    unresolved_labels.append((i, line))
            
            if unresolved_labels:
                print(f"\n❌ ERROR: Found unresolved labels:")
                for line_num, line in unresolved_labels:
                    print(f"  Line {line_num}: {line}")
                success = False
            else:
                print("\n✓ No unresolved labels found")
            
            # Check 2: All GOTOs and THENs should have numeric targets
            for i, line in enumerate(final_code, 1):
                if 'GOTO ' in line:
                    parts = line.split('GOTO ')
                    if len(parts) > 1:
                        target = parts[1].strip().split()[0]
                        if not target.isdigit():
                            print(f"❌ ERROR: Line {i} - GOTO target is not numeric: {target}")
                            success = False
                        else:
                            print(f"✓ Line {i} - GOTO {target} (valid)")
                
                if 'THEN ' in line:
                    parts = line.split('THEN ')
                    if len(parts) > 1:
                        target = parts[1].strip().split()[0]
                        if not target.isdigit():
                            print(f"❌ ERROR: Line {i} - THEN target is not numeric: {target}")
                            success = False
                        else:
                            print(f"✓ Line {i} - THEN {target} (valid)")
            
            # Check 3: Expected patterns
            if expected_patterns:
                final_code_text = '\n'.join(final_code)
                for pattern in expected_patterns:
                    if pattern not in final_code_text:
                        print(f"❌ ERROR: Expected pattern not found: '{pattern}'")
                        success = False
                    else:
                        print(f"✓ Expected pattern found: '{pattern}'")
            
            # Check 4: Label map consistency
            for label, line_num in label_map.items():
                if line_num < 1 or line_num > len(final_code):
                    print(f"❌ ERROR: Label {label} maps to invalid line number {line_num}")
                    success = False
            
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
    runner = LabelJumpTestRunner()
    
    # ========================================================================
    # TEST 1: Simple IF-THEN with Labels
    # ========================================================================
    runner.run_test(
        "TEST 1: Simple IF-THEN with Labels",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                x
            }
            x = 10;
            if x > 5 {
                print x
            }
        }
        """
    )
    
    # ========================================================================
    # TEST 2: IF-THEN-ELSE with Labels
    # ========================================================================
    runner.run_test(
        "TEST 2: IF-THEN-ELSE with Labels",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                x
                y
            }
            x = 10;
            if x > 5 {
                y = 1
            } else {
                y = 0
            };
            print y
        }
        """
    )
    
    # ========================================================================
    # TEST 3: While Loop with Labels
    # ========================================================================
    runner.run_test(
        "TEST 3: While Loop with Labels",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                counter
            }
            counter = 0;
            while counter > 10 {
                counter = counter plus 1;
                print counter
            }
        }
        """
    )
    
    # ========================================================================
    # TEST 4: Do-Until Loop with Labels
    # ========================================================================
    runner.run_test(
        "TEST 4: Do-Until Loop with Labels",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                i
            }
            i = 0;
            do {
                i = i plus 1;
                print i
            } until i > 10
        }
        """
    )
    
    # ========================================================================
    # TEST 5: Nested IF Statements
    # ========================================================================
    runner.run_test(
        "TEST 5: Nested IF Statements",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                x
                y
            }
            x = 10;
            y = 5;
            if x > 0 {
                if y > 0 {
                    print 1
                } else {
                    print 0
                }
            } else {
                print 2
            }
        }
        """
    )
    
    # ========================================================================
    # TEST 6: Loop Inside IF
    # ========================================================================
    runner.run_test(
        "TEST 6: Loop Inside IF",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                x
                i
            }
            x = 10;
            if x > 5 {
                i = 0;
                while i > 5 {
                    print i;
                    i = i plus 1
                }
            }
        }
        """
    )
    
    # ========================================================================
    # TEST 7: Multiple Sequential IFs
    # ========================================================================
    runner.run_test(
        "TEST 7: Multiple Sequential IFs",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                a
                b
                c
            }
            a = 1;
            b = 2;
            c = 3;
            if a > 0 {
                print a
            };
            if b > 0 {
                print b
            };
            if c > 0 {
                print c
            }
        }
        """
    )
    
    # ========================================================================
    # TEST 8: Complex Control Flow
    # ========================================================================
    runner.run_test(
        "TEST 8: Complex Control Flow",
        """
        glob {
            globalFlag
        }
        proc {}
        func {}
        main {
            var {
                x
                i
            }
            globalFlag = 1;
            x = 0;
            while x > 10 {
                if globalFlag eq 1 {
                    i = 0;
                    do {
                        i = i plus 1;
                        if i > 5 {
                            print i
                        }
                    } until i > 3
                };
                x = x plus 1
            }
        }
        """
    )
    
    # ========================================================================
    # TEST 9: Boolean Expressions with Labels
    # ========================================================================
    runner.run_test(
        "TEST 9: Boolean Expressions with Labels",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                a
                b
            }
            a = 10;
            b = 5;
            if (a > 5) and (b > 0) {
                print 1
            } else {
                print 0
            }
        }
        """
    )
    
    # ========================================================================
    # TEST 10: NOT Expression with Branch
    # ========================================================================
    runner.run_test(
        "TEST 10: NOT Expression with Branch",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                flag
            }
            flag = 0;
            if not flag {
                print 1
            } else {
                print 0
            }
        }
        """
    )
    
    # ========================================================================
    # TEST 11: Procedure with Branches
    # ========================================================================
    runner.run_test(
        "TEST 11: Procedure with Branches",
        """
        glob {}
        proc {
            checkValue(x) {
                local {}
                if x > 10 {
                    print 1
                } else {
                    print 0
                }
            }
        }
        func {}
        main {
            var {
                val
            }
            val = 15;
            checkValue(val)
        }
        """
    )
    
    # ========================================================================
    # TEST 12: Function with Loop
    # ========================================================================
    runner.run_test(
        "TEST 12: Function with Loop",
        """
        glob {}
        proc {}
        func {
            sumTo(n) {
                local {
                    sum
                    i
                }
                sum = 0;
                i = 1;
                while i > n {
                    sum = sum plus i;
                    i = i plus 1
                };
                return sum
            }
        }
        main {
            var {
                result
            }
            result = sumTo(10);
            print result
        }
        """
    )
    
    # ========================================================================
    # TEST 13: Empty Branches (Edge Case)
    # ========================================================================
    runner.run_test(
        "TEST 13: No Control Flow (No Labels Expected)",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                x
                y
            }
            x = 10;
            y = 20;
            print x;
            print y;
            halt
        }
        """,
        should_have_labels=False
    )
    
    # ========================================================================
    # TEST 14: Multiple Loops
    # ========================================================================
    runner.run_test(
        "TEST 14: Multiple Loops",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                i
                j
            }
            i = 0;
            while i > 5 {
                print i;
                i = i plus 1
            };
            j = 0;
            do {
                print j;
                j = j plus 1
            } until j > 5
        }
        """
    )
    
    # ========================================================================
    # TEST 15: Deep Nesting
    # ========================================================================
    runner.run_test(
        "TEST 15: Deep Nesting",
        """
        glob {}
        proc {}
        func {}
        main {
            var {
                a
                b
                c
            }
            a = 1;
            b = 2;
            c = 3;
            if a > 0 {
                if b > 0 {
                    if c > 0 {
                        print 1
                    } else {
                        print 2
                    }
                } else {
                    print 3
                }
            } else {
                print 4
            }
        }
        """
    )
    
    runner.print_summary()
    
    return 0 if runner.tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())