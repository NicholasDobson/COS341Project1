#!/usr/bin/env python3
"""
Enhanced Symbol Table Test - Testing 100% CRUD and Scope Management
Tests the newly added features for full compliance
"""

import sys
sys.path.insert(0, '.')

from compiler import SymbolTable, SymbolInfo, ScopeType, VarType

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def test_enhanced_crud():
    """Test enhanced CRUD operations with all new methods"""
    print_section("ENHANCED CRUD OPERATIONS TEST")
    
    st = SymbolTable()
    
    print("\n1. CREATE with return value and validation:")
    node1 = st.get_node_id()
    symbol1 = SymbolInfo(name="x", node_id=node1, scope=ScopeType.GLOBAL, 
                         var_type=VarType.NUMERIC, is_global=True)
    result = st.add_symbol(symbol1)
    assert result == True, "❌ add_symbol should return True"
    print(f"   ✅ add_symbol returned: {result}")
    
    # Try to add duplicate node_id
    duplicate = SymbolInfo(name="y", node_id=node1, scope=ScopeType.GLOBAL,
                           var_type=VarType.NUMERIC, is_global=True)
    result = st.add_symbol(duplicate)
    assert result == False, "❌ add_symbol should return False for duplicate node_id"
    print(f"   ✅ Duplicate node_id prevented: {result}")
    
    print("\n2. READ with multiple methods:")
    # Test get_symbol
    retrieved = st.get_symbol(node1)
    assert retrieved is not None, "❌ get_symbol failed"
    assert retrieved.name == "x", "❌ get_symbol returned wrong symbol"
    print(f"   ✅ get_symbol(node_id): {retrieved.name}")
    
    # Test get_symbol_by_name
    by_name = st.get_symbol_by_name("x")
    assert by_name is not None, "❌ get_symbol_by_name failed"
    assert by_name.name == "x", "❌ get_symbol_by_name wrong result"
    print(f"   ✅ get_symbol_by_name('x'): {by_name.name}")
    
    # Test get_symbol_by_name with scope filter
    by_name_scope = st.get_symbol_by_name("x", ScopeType.GLOBAL)
    assert by_name_scope is not None, "❌ get_symbol_by_name with scope failed"
    print(f"   ✅ get_symbol_by_name('x', GLOBAL): {by_name_scope.name}")
    
    # Test get_all_symbols_in_scope
    global_symbols = st.get_all_symbols_in_scope(ScopeType.GLOBAL)
    assert len(global_symbols) == 1, "❌ get_all_symbols_in_scope wrong count"
    print(f"   ✅ get_all_symbols_in_scope(GLOBAL): {len(global_symbols)} symbols")
    
    print("\n3. UPDATE with dedicated method:")
    success = st.update_symbol(node1, internal_name="x_renamed", var_type=VarType.BOOLEAN)
    assert success == True, "❌ update_symbol failed"
    updated = st.get_symbol(node1)
    assert updated.internal_name == "x_renamed", "❌ update didn't change internal_name"
    assert updated.var_type == VarType.BOOLEAN, "❌ update didn't change var_type"
    print(f"   ✅ update_symbol succeeded: internal_name='{updated.internal_name}'")
    print(f"   ✅ Multiple fields updated: var_type={updated.var_type.value}")
    
    # Test update on non-existent symbol
    success = st.update_symbol(9999, name="fake")
    assert success == False, "❌ update_symbol should fail for non-existent symbol"
    print(f"   ✅ update_symbol properly handles missing symbols: {success}")
    
    print("\n4. DELETE with proper cleanup:")
    # Add another symbol
    node2 = st.get_node_id()
    symbol2 = SymbolInfo(name="y", node_id=node2, scope=ScopeType.MAIN,
                         var_type=VarType.NUMERIC, is_main_var=True)
    st.add_symbol(symbol2)
    
    # Verify var_lookup has both
    assert "x" in st.var_lookup, "❌ x not in var_lookup"
    assert "y" in st.var_lookup, "❌ y not in var_lookup"
    
    # Delete first symbol
    success = st.delete_symbol(node1)
    assert success == True, "❌ delete_symbol failed"
    assert node1 not in st.symbols, "❌ Symbol still in symbols dict"
    assert "x" not in st.var_lookup, "❌ Symbol not removed from var_lookup"
    print(f"   ✅ delete_symbol returned: {success}")
    print(f"   ✅ Symbol removed from symbols dict")
    print(f"   ✅ Symbol removed from var_lookup index")
    
    # Try to delete non-existent symbol
    success = st.delete_symbol(9999)
    assert success == False, "❌ delete_symbol should return False for non-existent"
    print(f"   ✅ delete_symbol handles missing symbols: {success}")
    
    print("\n5. CLEAR utility:")
    st.clear()
    assert len(st.symbols) == 0, "❌ clear didn't empty symbols"
    assert len(st.var_lookup) == 0, "❌ clear didn't empty var_lookup"
    assert len(st.scope_stack) == 0, "❌ clear didn't empty scope_stack"
    print(f"   ✅ clear() emptied all data structures")

def test_scope_stack():
    """Test scope stack operations"""
    print_section("SCOPE STACK OPERATIONS TEST")
    
    st = SymbolTable()
    
    print("\n1. Push/Pop scope operations:")
    # Push global scope
    st.push_scope(ScopeType.GLOBAL, "global")
    assert st.scope_depth() == 1, "❌ Scope depth should be 1"
    assert st.get_current_scope_type() == ScopeType.GLOBAL, "❌ Current scope should be GLOBAL"
    print(f"   ✅ Pushed GLOBAL scope, depth: {st.scope_depth()}")
    
    # Push local scope
    st.push_scope(ScopeType.LOCAL, "myfunction", {"function_name": "myfunction"})
    assert st.scope_depth() == 2, "❌ Scope depth should be 2"
    assert st.get_current_scope_type() == ScopeType.LOCAL, "❌ Current scope should be LOCAL"
    print(f"   ✅ Pushed LOCAL scope, depth: {st.scope_depth()}")
    
    # Push another local scope (nested)
    st.push_scope(ScopeType.LOCAL, "inner", {"nested": True})
    assert st.scope_depth() == 3, "❌ Scope depth should be 3"
    print(f"   ✅ Pushed nested LOCAL scope, depth: {st.scope_depth()}")
    
    # Pop scope
    popped = st.pop_scope()
    assert popped is not None, "❌ pop_scope should return scope info"
    assert popped['name'] == "inner", "❌ Popped wrong scope"
    assert st.scope_depth() == 2, "❌ Scope depth should be 2 after pop"
    assert st.get_current_scope_type() == ScopeType.LOCAL, "❌ Current scope should revert to LOCAL"
    print(f"   ✅ Popped scope '{popped['name']}', depth now: {st.scope_depth()}")
    
    print("\n2. Current scope and parent scope:")
    current = st.current_scope()
    assert current is not None, "❌ current_scope should not be None"
    assert current['name'] == "myfunction", "❌ Current scope has wrong name"
    print(f"   ✅ current_scope(): {current['name']}")
    
    parent = st.get_parent_scope()
    assert parent is not None, "❌ get_parent_scope should not be None"
    assert parent['type'] == ScopeType.GLOBAL, "❌ Parent should be GLOBAL"
    print(f"   ✅ get_parent_scope(): {parent['type'].value}")
    
    print("\n3. Symbols tracked in scopes:")
    # Add symbols to current scope
    node1 = st.get_node_id()
    sym1 = SymbolInfo(name="local_var", node_id=node1, scope=ScopeType.LOCAL,
                      var_type=VarType.NUMERIC, is_local=True)
    st.add_symbol(sym1)
    
    node2 = st.get_node_id()
    sym2 = SymbolInfo(name="param", node_id=node2, scope=ScopeType.LOCAL,
                      var_type=VarType.NUMERIC, is_parameter=True)
    st.add_symbol(sym2)
    
    current = st.current_scope()
    assert len(current['symbols']) == 2, "❌ Scope should track 2 symbols"
    assert node1 in current['symbols'], "❌ Scope missing symbol node_id"
    assert node2 in current['symbols'], "❌ Scope missing symbol node_id"
    print(f"   ✅ Current scope tracks {len(current['symbols'])} symbols")
    print(f"   ✅ Symbol node_ids in scope: {current['symbols']}")
    
    print("\n4. Scope context tracking:")
    context = current.get('context', {})
    assert 'function_name' in context, "❌ Context missing function_name"
    assert context['function_name'] == "myfunction", "❌ Wrong function name in context"
    print(f"   ✅ Scope context preserved: function_name='{context['function_name']}'")
    
    print("\n5. Complete scope cleanup:")
    st.pop_scope()
    st.pop_scope()
    assert st.scope_depth() == 0, "❌ All scopes should be popped"
    assert st.get_current_scope_type() is None, "❌ Current scope should be None"
    print(f"   ✅ All scopes popped, depth: {st.scope_depth()}")

def test_improved_lookup():
    """Test improved lookup_var with scope resolution"""
    print_section("IMPROVED SCOPE RESOLUTION TEST")
    
    st = SymbolTable()
    
    print("\n1. Setup multi-scope environment:")
    # Global variable
    node_global = st.get_node_id()
    global_var = SymbolInfo(name="x", node_id=node_global, scope=ScopeType.GLOBAL,
                            var_type=VarType.NUMERIC, is_global=True)
    st.add_symbol(global_var)
    print(f"   ✅ Added global variable 'x' (node_{node_global})")
    
    # Main variable with same name
    node_main = st.get_node_id()
    main_var = SymbolInfo(name="x", node_id=node_main, scope=ScopeType.MAIN,
                          var_type=VarType.NUMERIC, is_main_var=True)
    st.add_symbol(main_var)
    print(f"   ✅ Added main variable 'x' (node_{node_main})")
    
    # Local variable with same name
    node_local = st.get_node_id()
    local_var = SymbolInfo(name="x", node_id=node_local, scope=ScopeType.LOCAL,
                           var_type=VarType.NUMERIC, is_local=True)
    st.add_symbol(local_var)
    print(f"   ✅ Added local variable 'x' (node_{node_local})")
    
    print("\n2. Scope-aware lookup resolution:")
    # Lookup in GLOBAL scope - should get global var
    result = st.lookup_var("x", ScopeType.GLOBAL)
    assert result is not None, "❌ lookup_var(GLOBAL) failed"
    assert result.node_id == node_global, "❌ GLOBAL scope should see global var"
    assert result.is_global == True, "❌ Should be global var"
    print(f"   ✅ lookup_var('x', GLOBAL) → node_{result.node_id} (is_global={result.is_global})")
    
    # Lookup in MAIN scope - should get main var (shadowing global)
    result = st.lookup_var("x", ScopeType.MAIN)
    assert result is not None, "❌ lookup_var(MAIN) failed"
    assert result.is_main_var == True, "❌ MAIN scope should see main var first"
    print(f"   ✅ lookup_var('x', MAIN) → node_{result.node_id} (is_main_var={result.is_main_var})")
    
    # Lookup in LOCAL scope - should get local var (shadowing others)
    result = st.lookup_var("x", ScopeType.LOCAL)
    assert result is not None, "❌ lookup_var(LOCAL) failed"
    assert result.is_local == True, "❌ LOCAL scope should see local var first"
    print(f"   ✅ lookup_var('x', LOCAL) → node_{result.node_id} (is_local={result.is_local})")
    
    print("\n3. Test fallback to global in local scope:")
    # Add a variable only in global scope
    node_only_global = st.get_node_id()
    only_global = SymbolInfo(name="globalonly", node_id=node_only_global,
                             scope=ScopeType.GLOBAL, var_type=VarType.NUMERIC,
                             is_global=True)
    st.add_symbol(only_global)
    
    # Lookup in LOCAL scope - should fall back to global
    result = st.lookup_var("globalonly", ScopeType.LOCAL)
    assert result is not None, "❌ LOCAL should see global vars"
    assert result.is_global == True, "❌ Should be the global var"
    print(f"   ✅ lookup_var('globalonly', LOCAL) → sees global (fallback works)")
    
    print("\n4. Test current scope type usage:")
    st.push_scope(ScopeType.MAIN)
    st.current_scope_type = ScopeType.MAIN
    
    # Lookup without explicit scope - should use current
    result = st.lookup_var("x")
    assert result is not None, "❌ lookup_var without scope failed"
    assert result.is_main_var == True, "❌ Should use current scope (MAIN)"
    print(f"   ✅ lookup_var('x') with current_scope=MAIN → node_{result.node_id}")

def test_error_formatting():
    """Test enhanced error formatting methods"""
    print_section("ENHANCED ERROR FORMATTING TEST")
    
    st = SymbolTable()
    
    print("\n1. Type error formatting:")
    st.add_type_error("Expected numeric, got boolean")
    assert any("TYPE-ERROR" in err for err in st.errors), "❌ Type error not formatted"
    print(f"   ✅ {st.errors[-1]}")
    
    st.add_type_error("Invalid operator for type", line=42)
    assert "Line 42" in st.errors[-1], "❌ Line number not included"
    print(f"   ✅ {st.errors[-1]}")
    
    print("\n2. Name error formatting:")
    st.add_name_error("Duplicate declaration of 'x'")
    assert any("NAME-RULE-VIOLATION" in err for err in st.errors), "❌ Name error not formatted"
    print(f"   ✅ {st.errors[-1]}")
    
    st.add_name_error("Variable shadows parameter", line=15)
    assert "Line 15" in st.errors[-1], "❌ Line number not included"
    print(f"   ✅ {st.errors[-1]}")
    
    print(f"\n   ✅ Total formatted errors: {len(st.errors)}")

def run_enhanced_tests():
    """Run all enhanced tests"""
    print("\n" + "="*70)
    print("  ENHANCED SYMBOL TABLE TEST SUITE")
    print("  Testing 100% CRUD and Scope Management")
    print("="*70)
    
    try:
        test_enhanced_crud()
        test_scope_stack()
        test_improved_lookup()
        test_error_formatting()
        
        print_section("FINAL RESULTS - ENHANCED FEATURES")
        print("\n✅ ALL ENHANCED TESTS PASSED!")
        print("\n100% Feature Compliance Achieved:")
        print("  ✅ CRUD Operations: 100%")
        print("     - Enhanced add_symbol with return value")
        print("     - Multiple read methods (get_symbol, get_symbol_by_name, etc.)")
        print("     - Dedicated update_symbol method")
        print("     - Proper delete_symbol with cleanup")
        print("     - clear() utility method")
        print("\n  ✅ Scope Management: 100%")
        print("     - Explicit scope stack (push/pop)")
        print("     - Current scope tracking")
        print("     - Parent scope navigation")
        print("     - Scope context preservation")
        print("     - Symbol tracking per scope")
        print("     - Improved scope-aware lookup")
        print("\n  ✅ Error Reporting: Enhanced")
        print("     - Type-specific error formatting")
        print("     - Line number support")
        print("     - Standardized error messages")
        print("\n" + "="*70 + "\n")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_enhanced_tests()
    sys.exit(0 if success else 1)
