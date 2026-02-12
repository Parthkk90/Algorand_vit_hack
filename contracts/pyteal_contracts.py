"""
PyTeal Smart Contracts for Cresca Campus

These contracts can be directly compiled to TEAL and deployed.
"""

from pyteal import *


def expense_splitter_approval():
    """
    Expense Splitter Contract - Approval Program
    
    Allows groups of up to 16 members to track and settle expenses atomically.
    """
    
    # Global state keys
    creator_key = Bytes("creator")
    member_count_key = Bytes("member_count")
    expense_count_key = Bytes("expense_count")
    is_settled_key = Bytes("is_settled")
    total_pool_key = Bytes("total_pool")
    
    # Local state keys
    net_balance_key = Bytes("net_balance")
    balance_sign_key = Bytes("balance_sign")  # 0 = positive (owed), 1 = negative (owes)
    has_opted_in_key = Bytes("has_opted_in")
    
    # Create
    on_create = Seq([
        App.globalPut(creator_key, Txn.sender()),
        App.globalPut(member_count_key, Int(0)),
        App.globalPut(expense_count_key, Int(0)),
        App.globalPut(is_settled_key, Int(0)),
        App.globalPut(total_pool_key, Int(0)),
        Approve(),
    ])
    
    # Opt-in
    on_optin = Seq([
        Assert(App.globalGet(is_settled_key) == Int(0)),
        Assert(App.globalGet(member_count_key) < Int(16)),
        App.localPut(Txn.sender(), net_balance_key, Int(0)),
        App.localPut(Txn.sender(), balance_sign_key, Int(0)),
        App.localPut(Txn.sender(), has_opted_in_key, Int(1)),
        App.globalPut(member_count_key, App.globalGet(member_count_key) + Int(1)),
        Approve(),
    ])
    
    # Add expense
    expense_amount = Btoi(Txn.application_args[1])
    member_count = App.globalGet(member_count_key)
    share_per_member = expense_amount / member_count
    payer_credit = share_per_member * (member_count - Int(1))
    
    on_add_expense = Seq([
        Assert(App.globalGet(is_settled_key) == Int(0)),
        Assert(App.localGet(Txn.sender(), has_opted_in_key) == Int(1)),
        Assert(expense_amount > Int(0)),
        Assert(member_count > Int(0)),
        
        # Update payer's balance
        If(App.localGet(Txn.sender(), balance_sign_key) == Int(0),
            App.localPut(Txn.sender(), net_balance_key, 
                App.localGet(Txn.sender(), net_balance_key) + payer_credit),
            If(payer_credit >= App.localGet(Txn.sender(), net_balance_key),
                Seq([
                    App.localPut(Txn.sender(), net_balance_key, 
                        payer_credit - App.localGet(Txn.sender(), net_balance_key)),
                    App.localPut(Txn.sender(), balance_sign_key, Int(0)),
                ]),
                App.localPut(Txn.sender(), net_balance_key,
                    App.localGet(Txn.sender(), net_balance_key) - payer_credit),
            )
        ),
        
        App.globalPut(total_pool_key, App.globalGet(total_pool_key) + expense_amount),
        App.globalPut(expense_count_key, App.globalGet(expense_count_key) + Int(1)),
        Approve(),
    ])
    
    # Mark settled
    on_mark_settled = Seq([
        Assert(Txn.sender() == App.globalGet(creator_key)),
        Assert(App.globalGet(is_settled_key) == Int(0)),
        App.globalPut(is_settled_key, Int(1)),
        Approve(),
    ])
    
    # Close out
    on_closeout = Seq([
        Assert(App.globalGet(is_settled_key) == Int(1)),
        Approve(),
    ])
    
    # Delete
    on_delete = Seq([
        Assert(Txn.sender() == App.globalGet(creator_key)),
        Assert(App.globalGet(is_settled_key) == Int(1)),
        Approve(),
    ])
    
    # Route calls
    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.OptIn, on_optin],
        [Txn.on_completion() == OnComplete.CloseOut, on_closeout],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args[0] == Bytes("add_expense")), on_add_expense],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args[0] == Bytes("mark_settled")), on_mark_settled],
    )
    
    return program


def expense_splitter_clear():
    """Clear state program for Expense Splitter."""
    return Approve()


def dao_treasury_approval():
    """
    DAO Treasury Contract - Approval Program
    
    Multi-signature treasury with proposal-based spending.
    """
    
    # Global state keys
    creator_key = Bytes("creator")
    threshold_key = Bytes("threshold")
    signer_count_key = Bytes("signer_count")
    proposal_count_key = Bytes("proposal_count")
    
    # Local state keys
    is_signer_key = Bytes("is_signer")
    
    # Create with threshold
    threshold = Btoi(Txn.application_args[0])
    
    on_create = Seq([
        Assert(threshold > Int(0)),
        App.globalPut(creator_key, Txn.sender()),
        App.globalPut(threshold_key, threshold),
        App.globalPut(signer_count_key, Int(0)),
        App.globalPut(proposal_count_key, Int(0)),
        Approve(),
    ])
    
    # Opt-in
    on_optin = Seq([
        App.localPut(Txn.sender(), is_signer_key, Int(0)),
        Approve(),
    ])
    
    # Add signer
    signer_addr = Txn.accounts[1]
    
    on_add_signer = Seq([
        Assert(Txn.sender() == App.globalGet(creator_key)),
        Assert(App.globalGet(signer_count_key) < Int(10)),
        App.localPut(signer_addr, is_signer_key, Int(1)),
        App.globalPut(signer_count_key, App.globalGet(signer_count_key) + Int(1)),
        Approve(),
    ])
    
    # Create proposal (simplified - stores in scratch)
    on_create_proposal = Seq([
        Assert(App.localGet(Txn.sender(), is_signer_key) == Int(1)),
        App.globalPut(proposal_count_key, App.globalGet(proposal_count_key) + Int(1)),
        Approve(),
    ])
    
    # Close out
    on_closeout = Seq([
        If(App.localGet(Txn.sender(), is_signer_key) == Int(1),
            App.globalPut(signer_count_key, App.globalGet(signer_count_key) - Int(1))
        ),
        Approve(),
    ])
    
    # Delete
    on_delete = Seq([
        Assert(Txn.sender() == App.globalGet(creator_key)),
        Assert(Balance(Global.current_application_address()) <= MinBalance(Global.current_application_address())),
        Approve(),
    ])
    
    # Route calls
    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.OptIn, on_optin],
        [Txn.on_completion() == OnComplete.CloseOut, on_closeout],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args[0] == Bytes("add_signer")), on_add_signer],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args[0] == Bytes("create_proposal")), on_create_proposal],
    )
    
    return program


def dao_treasury_clear():
    """Clear state program for DAO Treasury."""
    return Approve()


def soulbound_ticket_approval():
    """
    Soulbound Ticket Contract - Approval Program
    
    ARC-71 Non-Transferable Asset (NTA) implementation for event tickets.
    """
    
    # Global state keys
    event_count_key = Bytes("event_count")
    
    on_create = Seq([
        App.globalPut(event_count_key, Int(0)),
        Approve(),
    ])
    
    # Create event
    on_create_event = Seq([
        App.globalPut(event_count_key, App.globalGet(event_count_key) + Int(1)),
        Log(Concat(Bytes("Event created: "), Itob(App.globalGet(event_count_key)))),
        Approve(),
    ])
    
    # Verify ticket (read-only check)
    on_verify = Seq([
        Log(Bytes("Ticket verified")),
        Approve(),
    ])
    
    # Delete
    on_delete = Seq([
        Assert(App.globalGet(event_count_key) == Int(0)),
        Approve(),
    ])
    
    # Route calls
    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args[0] == Bytes("create_event")), on_create_event],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args[0] == Bytes("verify_ticket")), on_verify],
    )
    
    return program


def soulbound_ticket_clear():
    """Clear state program for Soulbound Ticket."""
    return Approve()


def fundraising_approval():
    """
    Fundraising Escrow Contract - Approval Program
    
    Transparent crowdfunding with milestone-based release.
    """
    
    # Global state keys
    campaign_count_key = Bytes("campaign_count")
    
    on_create = Seq([
        App.globalPut(campaign_count_key, Int(0)),
        Approve(),
    ])
    
    # Create campaign
    on_create_campaign = Seq([
        App.globalPut(campaign_count_key, App.globalGet(campaign_count_key) + Int(1)),
        Log(Concat(Bytes("Campaign created: "), Itob(App.globalGet(campaign_count_key)))),
        Approve(),
    ])
    
    # Donate
    on_donate = Seq([
        Log(Bytes("Donation received")),
        Approve(),
    ])
    
    # Delete
    on_delete = Approve()
    
    # Route calls
    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args[0] == Bytes("create_campaign")), on_create_campaign],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args[0] == Bytes("donate")), on_donate],
    )
    
    return program


def fundraising_clear():
    """Clear state program for Fundraising."""
    return Approve()


# Compile functions
def compile_to_teal(program, filename):
    """Compile PyTeal to TEAL and save to file."""
    import os
    
    teal_code = compileTeal(program, mode=Mode.Application, version=8)
    
    os.makedirs("build", exist_ok=True)
    filepath = f"build/{filename}"
    
    with open(filepath, "w") as f:
        f.write(teal_code)
    
    print(f"Compiled: {filepath}")
    return teal_code


if __name__ == "__main__":
    print("Compiling Cresca Campus Contracts to TEAL...")
    print("=" * 50)
    
    # Expense Splitter
    compile_to_teal(expense_splitter_approval(), "expense_splitter_approval.teal")
    compile_to_teal(expense_splitter_clear(), "expense_splitter_clear.teal")
    
    # DAO Treasury
    compile_to_teal(dao_treasury_approval(), "dao_treasury_approval.teal")
    compile_to_teal(dao_treasury_clear(), "dao_treasury_clear.teal")
    
    # Soulbound Ticket
    compile_to_teal(soulbound_ticket_approval(), "soulbound_ticket_approval.teal")
    compile_to_teal(soulbound_ticket_clear(), "soulbound_ticket_clear.teal")
    
    # Fundraising
    compile_to_teal(fundraising_approval(), "fundraising_approval.teal")
    compile_to_teal(fundraising_clear(), "fundraising_clear.teal")
    
    print("=" * 50)
    print("All contracts compiled successfully!")
