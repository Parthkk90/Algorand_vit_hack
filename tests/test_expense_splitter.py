"""
Tests for Expense Splitter Smart Contract

Tests cover:
- Contract creation
- Member opt-in
- Adding expenses
- Balance calculations
- Settlement marking
"""

import pytest
from algopy_testing import AlgopyTestContext, algopy_testing_context
from contracts.expense_splitter.contract import ExpenseSplitter


class TestExpenseSplitter:
    """Test suite for ExpenseSplitter contract."""
    
    @pytest.fixture
    def context(self) -> AlgopyTestContext:
        """Create a fresh testing context for each test."""
        with algopy_testing_context() as ctx:
            yield ctx
    
    def test_create_split(self, context: AlgopyTestContext):
        """Test creating a new expense split."""
        # Arrange
        creator = context.default_sender
        
        # Act
        contract = ExpenseSplitter()
        contract.create()
        
        # Assert
        assert contract.creator.value == creator
        assert contract.member_count.value == 0
        assert contract.expense_count.value == 0
        assert contract.is_settled.value == 0
        assert contract.total_pool.value == 0
    
    def test_opt_in_member(self, context: AlgopyTestContext):
        """Test member opting into a split."""
        # Arrange
        contract = ExpenseSplitter()
        contract.create()
        
        member = context.any.account()
        context.set_sender(member)
        
        # Act
        contract.opt_in()
        
        # Assert
        assert contract.member_count.value == 1
        assert contract.has_opted_in[member] == 1
        assert contract.net_balance[member] == 0
    
    def test_max_members_limit(self, context: AlgopyTestContext):
        """Test that we can't exceed 16 members."""
        # Arrange
        contract = ExpenseSplitter()
        contract.create()
        
        # Add 16 members
        for i in range(16):
            member = context.any.account()
            context.set_sender(member)
            contract.opt_in()
        
        # Act & Assert - 17th member should fail
        member_17 = context.any.account()
        context.set_sender(member_17)
        
        with pytest.raises(AssertionError, match="Max members reached"):
            contract.opt_in()
    
    def test_add_expense(self, context: AlgopyTestContext):
        """Test adding an expense."""
        # Arrange
        contract = ExpenseSplitter()
        contract.create()
        
        payer = context.any.account()
        context.set_sender(payer)
        contract.opt_in()
        
        # Add another member
        member2 = context.any.account()
        context.set_sender(member2)
        contract.opt_in()
        
        # Act - payer adds expense
        context.set_sender(payer)
        from algopy.arc4 import UInt64 as ARC4UInt64, String
        contract.add_expense(ARC4UInt64(100_000), String("Dinner"))
        
        # Assert
        assert contract.expense_count.value == 1
        assert contract.total_pool.value == 100_000
    
    def test_get_balance(self, context: AlgopyTestContext):
        """Test getting member balance."""
        # Arrange
        contract = ExpenseSplitter()
        contract.create()
        
        payer = context.any.account()
        context.set_sender(payer)
        contract.opt_in()
        
        # Act
        from algopy.arc4 import Address
        result = contract.get_balance(Address(payer.bytes))
        
        # Assert - initial balance should be 0
        balance, is_owed = result.native
        assert balance == 0
    
    def test_cannot_add_expense_when_settled(self, context: AlgopyTestContext):
        """Test that expenses can't be added after settlement."""
        # Arrange
        contract = ExpenseSplitter()
        contract.create()
        
        creator = context.default_sender
        contract.opt_in()
        
        contract.mark_settled()
        
        # Act & Assert
        from algopy.arc4 import UInt64 as ARC4UInt64, String
        with pytest.raises(AssertionError, match="Split already settled"):
            contract.add_expense(ARC4UInt64(100_000), String("Late expense"))
    
    def test_get_split_info(self, context: AlgopyTestContext):
        """Test getting split information."""
        # Arrange
        contract = ExpenseSplitter()
        contract.create()
        
        member = context.any.account()
        context.set_sender(member)
        contract.opt_in()
        
        # Act
        result = contract.get_split_info()
        member_count, expense_count, total_pool, is_settled = result.native
        
        # Assert
        assert member_count == 1
        assert expense_count == 0
        assert total_pool == 0
        assert is_settled == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
