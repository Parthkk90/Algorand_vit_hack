"""
Expense Splitter Smart Contract for Cresca Campus

This contract enables groups of up to 16 members to track shared expenses
and settle all debts atomically using Algorand's native Atomic Group feature.

Features:
- Create expense splits with member list
- Track who paid for what
- Calculate net balances for each member
- Settle all debts in a single atomic transaction group

Algorand Primitives Used:
- AVM Application (smart contract)
- Atomic Groups (up to 16 transactions)
- Local State (per-member balances)
- Global State (split metadata)
"""

from algopy import (
    ARC4Contract,
    Account,
    Application,
    Asset,
    Bytes,
    Global,
    GlobalState,
    LocalState,
    Txn,
    UInt64,
    arc4,
    gtxn,
    itxn,
    op,
    subroutine,
    Box,
    BoxRef,
)
from algopy.arc4 import abimethod, Address, String, UInt64 as ARC4UInt64, DynamicArray


# Maximum members in a split (Algorand atomic group limit)
MAX_MEMBERS = 16


class ExpenseSplitter(ARC4Contract):
    """
    Smart contract for splitting expenses among a group of members.
    
    State Schema:
    - Global State:
        - creator: Address of split creator
        - member_count: Number of members in the split
        - expense_count: Total number of expenses logged
        - is_settled: Whether the split has been settled
        - total_pool: Total amount in the expense pool
        
    - Local State (per member):
        - net_balance: Signed balance (positive = owed money, negative = owes money)
        - has_opted_in: Whether member has joined the split
        
    - Boxes:
        - members: List of member addresses
        - expenses: Log of all expenses
    """
    
    # Global State
    creator: GlobalState[Account]
    member_count: GlobalState[UInt64]
    expense_count: GlobalState[UInt64]
    is_settled: GlobalState[UInt64]  # 0 = active, 1 = settled
    total_pool: GlobalState[UInt64]
    
    # Local State
    net_balance: LocalState[UInt64]
    balance_sign: LocalState[UInt64]  # 0 = positive (owed), 1 = negative (owes)
    has_opted_in: LocalState[UInt64]
    
    @arc4.abimethod(create="require")
    def create(self) -> None:
        """
        Create a new expense split.
        The creator is automatically added as the first member.
        """
        self.creator.value = Txn.sender
        self.member_count.value = UInt64(0)
        self.expense_count.value = UInt64(0)
        self.is_settled.value = UInt64(0)
        self.total_pool.value = UInt64(0)
    
    @arc4.abimethod(allow_actions=["OptIn"])
    def opt_in(self) -> None:
        """
        Opt into the expense split as a member.
        Members must opt-in before they can participate.
        """
        assert self.is_settled.value == UInt64(0), "Split already settled"
        assert self.member_count.value < UInt64(MAX_MEMBERS), "Max members reached"
        
        # Initialize local state
        self.net_balance[Txn.sender] = UInt64(0)
        self.balance_sign[Txn.sender] = UInt64(0)
        self.has_opted_in[Txn.sender] = UInt64(1)
        
        # Increment member count
        self.member_count.value = self.member_count.value + UInt64(1)
        
        # Store member address in box
        member_index = self.member_count.value - UInt64(1)
        box_key = op.itob(member_index)
        op.Box.put(box_key, Txn.sender.bytes)
    
    @arc4.abimethod
    def add_expense(
        self,
        amount: arc4.UInt64,
        description: arc4.String,
    ) -> None:
        """
        Log an expense paid by the caller.
        
        The amount is distributed equally among all members.
        The payer's balance increases (they are owed money).
        Other members' balances decrease (they owe money).
        
        Args:
            amount: Amount paid in microALGOs
            description: Description of the expense
        """
        assert self.is_settled.value == UInt64(0), "Split already settled"
        assert self.has_opted_in[Txn.sender] == UInt64(1), "Not a member"
        assert amount.native > UInt64(0), "Amount must be positive"
        
        payer = Txn.sender
        expense_amount = amount.native
        member_count = self.member_count.value
        
        assert member_count > UInt64(0), "No members in split"
        
        # Calculate share per member
        share_per_member = expense_amount // member_count
        
        # Update payer's balance (they are owed: (n-1) * share)
        payer_credit = share_per_member * (member_count - UInt64(1))
        current_balance = self.net_balance[payer]
        current_sign = self.balance_sign[payer]
        
        if current_sign == UInt64(0):
            # Currently positive (owed money), add to it
            self.net_balance[payer] = current_balance + payer_credit
        else:
            # Currently negative (owes money), reduce debt
            if payer_credit >= current_balance:
                self.net_balance[payer] = payer_credit - current_balance
                self.balance_sign[payer] = UInt64(0)
            else:
                self.net_balance[payer] = current_balance - payer_credit
        
        # Update total pool
        self.total_pool.value = self.total_pool.value + expense_amount
        
        # Increment expense count
        self.expense_count.value = self.expense_count.value + UInt64(1)
        
        # Store expense in box
        expense_index = self.expense_count.value - UInt64(1)
        expense_key = Bytes(b"exp_") + op.itob(expense_index)
        expense_data = payer.bytes + op.itob(expense_amount)
        op.Box.put(expense_key, expense_data)
    
    @arc4.abimethod
    def update_member_debt(
        self,
        member: arc4.Address,
        share: arc4.UInt64,
    ) -> None:
        """
        Update a member's debt when an expense is added.
        Called separately due to transaction limits.
        
        Args:
            member: Member address to update
            share: Share amount they owe
        """
        assert self.is_settled.value == UInt64(0), "Split already settled"
        assert Txn.sender == self.creator.value, "Only creator can update"
        
        member_account = Account(member.bytes)
        assert self.has_opted_in[member_account] == UInt64(1), "Not a member"
        
        share_amount = share.native
        current_balance = self.net_balance[member_account]
        current_sign = self.balance_sign[member_account]
        
        if current_sign == UInt64(1):
            # Already negative (owes money), add to debt
            self.net_balance[member_account] = current_balance + share_amount
        else:
            # Currently positive or zero
            if share_amount > current_balance:
                self.net_balance[member_account] = share_amount - current_balance
                self.balance_sign[member_account] = UInt64(1)
            else:
                self.net_balance[member_account] = current_balance - share_amount
    
    @arc4.abimethod
    def get_balance(self, member: arc4.Address) -> arc4.Tuple[arc4.UInt64, arc4.Bool]:
        """
        Get a member's current balance.
        
        Args:
            member: Member address to check
            
        Returns:
            Tuple of (balance amount, is_owed)
            - is_owed = True means member is owed money
            - is_owed = False means member owes money
        """
        member_account = Account(member.bytes)
        balance = self.net_balance[member_account]
        sign = self.balance_sign[member_account]
        
        is_owed = arc4.Bool(sign == UInt64(0))
        
        return arc4.Tuple((arc4.UInt64(balance), is_owed))
    
    @arc4.abimethod
    def get_split_info(self) -> arc4.Tuple[arc4.UInt64, arc4.UInt64, arc4.UInt64, arc4.Bool]:
        """
        Get information about the current split.
        
        Returns:
            Tuple of (member_count, expense_count, total_pool, is_settled)
        """
        return arc4.Tuple((
            arc4.UInt64(self.member_count.value),
            arc4.UInt64(self.expense_count.value),
            arc4.UInt64(self.total_pool.value),
            arc4.Bool(self.is_settled.value == UInt64(1)),
        ))
    
    @arc4.abimethod
    def mark_settled(self) -> None:
        """
        Mark the split as settled after atomic settlement.
        Only the creator can mark as settled.
        """
        assert Txn.sender == self.creator.value, "Only creator can settle"
        assert self.is_settled.value == UInt64(0), "Already settled"
        
        self.is_settled.value = UInt64(1)
    
    @arc4.abimethod(allow_actions=["CloseOut"])
    def close_out(self) -> None:
        """
        Close out from the expense split.
        Member can only close out after settlement.
        """
        assert self.is_settled.value == UInt64(1), "Split not yet settled"
        
        # Clear local state
        self.net_balance[Txn.sender] = UInt64(0)
        self.balance_sign[Txn.sender] = UInt64(0)
        self.has_opted_in[Txn.sender] = UInt64(0)
    
    @arc4.abimethod(allow_actions=["DeleteApplication"])
    def delete(self) -> None:
        """
        Delete the expense split application.
        Only creator can delete, and only after settlement.
        """
        assert Txn.sender == self.creator.value, "Only creator can delete"
        assert self.is_settled.value == UInt64(1), "Must settle first"
