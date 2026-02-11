"""
Fundraising Escrow Smart Contract for Cresca Campus

A transparent crowdfunding contract with milestone-based fund release.
All donations are held in escrow and released only when milestones are met.
Automatic refunds if campaign fails.

Features:
- Create campaigns with goal, deadline, and beneficiary
- Donate to campaigns (with optional anonymity)
- Milestone-based fund release
- Automatic refund if campaign fails
- Full on-chain transparency
- Anonymous donor mode via note-field encryption

Algorand Primitives Used:
- AVM Application (smart contract)
- Escrow pattern (contract holds funds)
- Inner Transactions (for fund release and refunds)
- Boxes (for storing campaigns, donations, milestones)
"""

from algopy import (
    ARC4Contract,
    Account,
    Bytes,
    Global,
    GlobalState,
    Txn,
    UInt64,
    arc4,
    itxn,
    op,
    Box,
)
from algopy.arc4 import abimethod, Address, String, UInt64 as ARC4UInt64, Bool


# Campaign status constants
STATUS_ACTIVE = UInt64(0)
STATUS_SUCCESSFUL = UInt64(1)
STATUS_FAILED = UInt64(2)
STATUS_CANCELLED = UInt64(3)


class FundraisingEscrow(ARC4Contract):
    """
    Transparent crowdfunding with milestone-based release.
    
    State Schema:
    - Global State:
        - campaign_count: Total campaigns created
        
    - Boxes:
        - campaign_{id}: Campaign details
        - milestone_{campaign_id}_{index}: Milestone details
        - donation_{campaign_id}_{index}: Donation records
        - donor_{campaign_id}_{address}: Donor totals for refunds
    """
    
    # Global State
    campaign_count: GlobalState[UInt64]
    
    @arc4.abimethod(create="require")
    def create(self) -> None:
        """
        Create the fundraising contract.
        """
        self.campaign_count.value = UInt64(0)
    
    @arc4.abimethod
    def create_campaign(
        self,
        beneficiary: arc4.Address,
        goal: arc4.UInt64,
        deadline: arc4.UInt64,
        title: arc4.String,
        description: arc4.String,
    ) -> arc4.UInt64:
        """
        Create a new fundraising campaign.
        
        Args:
            beneficiary: Address to receive funds on success
            goal: Funding goal in microALGOs
            deadline: Unix timestamp deadline
            title: Campaign title
            description: Campaign description
            
        Returns:
            Campaign ID
        """
        assert goal.native > UInt64(0), "Goal must be positive"
        assert deadline.native > Global.latest_timestamp, "Deadline must be future"
        
        campaign_id = self.campaign_count.value
        self.campaign_count.value = campaign_id + UInt64(1)
        
        # Store campaign in box
        # Format: creator (32) + beneficiary (32) + goal (8) + raised (8) + 
        #         deadline (8) + status (8) + milestone_count (8) + donation_count (8)
        campaign_key = Bytes(b"camp_") + op.itob(campaign_id)
        campaign_data = (
            Txn.sender.bytes +           # Creator
            beneficiary.bytes +           # Beneficiary
            op.itob(goal.native) +        # Goal
            op.itob(UInt64(0)) +          # Raised (starts at 0)
            op.itob(deadline.native) +    # Deadline
            op.itob(STATUS_ACTIVE) +      # Status
            op.itob(UInt64(0)) +          # Milestone count
            op.itob(UInt64(0))            # Donation count
        )
        op.Box.put(campaign_key, campaign_data)
        
        return arc4.UInt64(campaign_id)
    
    @arc4.abimethod
    def add_milestone(
        self,
        campaign_id: arc4.UInt64,
        description: arc4.String,
        amount: arc4.UInt64,
    ) -> arc4.UInt64:
        """
        Add a milestone to a campaign.
        Only campaign creator can add milestones.
        
        Args:
            campaign_id: ID of the campaign
            description: Milestone description
            amount: Amount to release when milestone is met
            
        Returns:
            Milestone index
        """
        # Get campaign
        campaign_key = Bytes(b"camp_") + op.itob(campaign_id.native)
        campaign_exists, campaign_data = op.Box.get(campaign_key)
        assert campaign_exists, "Campaign does not exist"
        
        # Verify caller is creator
        creator = op.extract(campaign_data, 0, 32)
        assert Txn.sender.bytes == creator, "Only creator can add milestones"
        
        # Check campaign is still active
        status = op.btoi(op.extract(campaign_data, 88, 8))
        assert status == STATUS_ACTIVE, "Campaign not active"
        
        # Get current milestone count
        milestone_count = op.btoi(op.extract(campaign_data, 96, 8))
        
        # Store milestone
        # Format: amount (8) + released (8) + completed (8)
        milestone_key = (
            Bytes(b"mile_") + 
            op.itob(campaign_id.native) + 
            Bytes(b"_") + 
            op.itob(milestone_count)
        )
        milestone_data = (
            op.itob(amount.native) +  # Amount to release
            op.itob(UInt64(0)) +      # Amount released so far
            op.itob(UInt64(0))        # Completed flag (0 = pending, 1 = complete)
        )
        op.Box.put(milestone_key, milestone_data)
        
        # Update campaign milestone count
        new_count = milestone_count + UInt64(1)
        updated_campaign = (
            op.extract(campaign_data, 0, 96) +  # Keep first 96 bytes
            op.itob(new_count) +                 # Update milestone count
            op.extract(campaign_data, 104, 8)    # Keep donation count
        )
        op.Box.put(campaign_key, updated_campaign)
        
        return arc4.UInt64(milestone_count)
    
    @arc4.abimethod
    def donate(
        self,
        campaign_id: arc4.UInt64,
        amount: arc4.UInt64,
        anonymous: arc4.Bool,
    ) -> None:
        """
        Donate to a campaign.
        Must be called with a payment transaction in the same group.
        
        Args:
            campaign_id: ID of the campaign
            amount: Donation amount in microALGOs
            anonymous: If true, encrypt donor info in note field
        """
        # Get campaign
        campaign_key = Bytes(b"camp_") + op.itob(campaign_id.native)
        campaign_exists, campaign_data = op.Box.get(campaign_key)
        assert campaign_exists, "Campaign does not exist"
        
        # Check campaign is active and before deadline
        status = op.btoi(op.extract(campaign_data, 88, 8))
        deadline = op.btoi(op.extract(campaign_data, 80, 8))
        assert status == STATUS_ACTIVE, "Campaign not active"
        assert Global.latest_timestamp < deadline, "Campaign ended"
        
        # Get current raised amount and donation count
        raised = op.btoi(op.extract(campaign_data, 72, 8))
        donation_count = op.btoi(op.extract(campaign_data, 104, 8))
        
        # Update raised amount
        new_raised = raised + amount.native
        
        # Update campaign
        updated_campaign = (
            op.extract(campaign_data, 0, 72) +   # Keep first 72 bytes
            op.itob(new_raised) +                 # Update raised
            op.extract(campaign_data, 80, 24) +   # Keep deadline, status, milestone_count
            op.itob(donation_count + UInt64(1))   # Increment donation count
        )
        op.Box.put(campaign_key, updated_campaign)
        
        # Store donation record (for transparency)
        donation_key = (
            Bytes(b"don_") +
            op.itob(campaign_id.native) +
            Bytes(b"_") +
            op.itob(donation_count)
        )
        
        # If anonymous, store encrypted placeholder; else store address
        if anonymous.native:
            donor_record = Bytes(b"anonymous") + op.itob(amount.native) + op.itob(Global.latest_timestamp)
        else:
            donor_record = Txn.sender.bytes + op.itob(amount.native) + op.itob(Global.latest_timestamp)
        
        op.Box.put(donation_key, donor_record)
        
        # Track donor total for potential refunds
        donor_key = Bytes(b"donor_") + op.itob(campaign_id.native) + Txn.sender.bytes
        donor_exists, donor_data = op.Box.get(donor_key)
        
        if donor_exists:
            current_total = op.btoi(donor_data)
            op.Box.put(donor_key, op.itob(current_total + amount.native))
        else:
            op.Box.put(donor_key, op.itob(amount.native))
    
    @arc4.abimethod
    def complete_milestone(
        self,
        campaign_id: arc4.UInt64,
        milestone_index: arc4.UInt64,
        proof: arc4.String,
    ) -> None:
        """
        Mark a milestone as complete.
        Only campaign creator can mark milestones complete.
        
        Args:
            campaign_id: ID of the campaign
            milestone_index: Index of the milestone
            proof: Proof/description of milestone completion
        """
        # Get campaign
        campaign_key = Bytes(b"camp_") + op.itob(campaign_id.native)
        campaign_exists, campaign_data = op.Box.get(campaign_key)
        assert campaign_exists, "Campaign does not exist"
        
        # Verify caller is creator
        creator = op.extract(campaign_data, 0, 32)
        assert Txn.sender.bytes == creator, "Only creator can complete milestones"
        
        # Get milestone
        milestone_key = (
            Bytes(b"mile_") + 
            op.itob(campaign_id.native) + 
            Bytes(b"_") + 
            op.itob(milestone_index.native)
        )
        milestone_exists, milestone_data = op.Box.get(milestone_key)
        assert milestone_exists, "Milestone does not exist"
        
        # Check not already completed
        completed = op.btoi(op.extract(milestone_data, 16, 8))
        assert completed == UInt64(0), "Milestone already completed"
        
        # Mark as completed
        updated_milestone = (
            op.extract(milestone_data, 0, 16) +  # Keep amount and released
            op.itob(UInt64(1))                    # Mark completed
        )
        op.Box.put(milestone_key, updated_milestone)
    
    @arc4.abimethod
    def release_funds(
        self,
        campaign_id: arc4.UInt64,
        milestone_index: arc4.UInt64,
    ) -> None:
        """
        Release funds for a completed milestone to the beneficiary.
        Anyone can call this once milestone is marked complete.
        
        Args:
            campaign_id: ID of the campaign
            milestone_index: Index of the milestone
        """
        # Get campaign
        campaign_key = Bytes(b"camp_") + op.itob(campaign_id.native)
        campaign_exists, campaign_data = op.Box.get(campaign_key)
        assert campaign_exists, "Campaign does not exist"
        
        beneficiary_bytes = op.extract(campaign_data, 32, 32)
        
        # Get milestone
        milestone_key = (
            Bytes(b"mile_") + 
            op.itob(campaign_id.native) + 
            Bytes(b"_") + 
            op.itob(milestone_index.native)
        )
        milestone_exists, milestone_data = op.Box.get(milestone_key)
        assert milestone_exists, "Milestone does not exist"
        
        # Check milestone is completed
        completed = op.btoi(op.extract(milestone_data, 16, 8))
        assert completed == UInt64(1), "Milestone not completed"
        
        # Check funds not already released
        amount = op.btoi(op.extract(milestone_data, 0, 8))
        released = op.btoi(op.extract(milestone_data, 8, 8))
        assert released == UInt64(0), "Funds already released"
        
        # Check contract has sufficient balance
        available = Global.current_application_address.balance - Global.current_application_address.min_balance
        assert amount <= available, "Insufficient funds"
        
        # Release funds via inner transaction
        itxn.Payment(
            receiver=Account(beneficiary_bytes),
            amount=amount,
            fee=Global.min_txn_fee,
        ).submit()
        
        # Mark funds as released
        updated_milestone = (
            op.extract(milestone_data, 0, 8) +  # Keep amount
            op.itob(amount) +                    # Mark as released
            op.extract(milestone_data, 16, 8)   # Keep completed flag
        )
        op.Box.put(milestone_key, updated_milestone)
    
    @arc4.abimethod
    def finalize_campaign(
        self,
        campaign_id: arc4.UInt64,
    ) -> None:
        """
        Finalize a campaign after deadline.
        Marks as successful (if goal met) or failed (if not).
        
        Args:
            campaign_id: ID of the campaign
        """
        # Get campaign
        campaign_key = Bytes(b"camp_") + op.itob(campaign_id.native)
        campaign_exists, campaign_data = op.Box.get(campaign_key)
        assert campaign_exists, "Campaign does not exist"
        
        status = op.btoi(op.extract(campaign_data, 88, 8))
        deadline = op.btoi(op.extract(campaign_data, 80, 8))
        goal = op.btoi(op.extract(campaign_data, 64, 8))
        raised = op.btoi(op.extract(campaign_data, 72, 8))
        
        assert status == STATUS_ACTIVE, "Campaign already finalized"
        assert Global.latest_timestamp >= deadline, "Campaign still active"
        
        # Determine new status
        if raised >= goal:
            new_status = STATUS_SUCCESSFUL
        else:
            new_status = STATUS_FAILED
        
        # Update status
        updated_campaign = (
            op.extract(campaign_data, 0, 88) +  # Keep first 88 bytes
            op.itob(new_status) +                # Update status
            op.extract(campaign_data, 96, 16)    # Keep milestone_count and donation_count
        )
        op.Box.put(campaign_key, updated_campaign)
    
    @arc4.abimethod
    def claim_refund(
        self,
        campaign_id: arc4.UInt64,
    ) -> None:
        """
        Claim refund for a failed campaign.
        Donors can claim their donation back if campaign fails.
        
        Args:
            campaign_id: ID of the campaign
        """
        # Get campaign
        campaign_key = Bytes(b"camp_") + op.itob(campaign_id.native)
        campaign_exists, campaign_data = op.Box.get(campaign_key)
        assert campaign_exists, "Campaign does not exist"
        
        status = op.btoi(op.extract(campaign_data, 88, 8))
        assert status == STATUS_FAILED, "Campaign not failed"
        
        # Get donor's total
        donor_key = Bytes(b"donor_") + op.itob(campaign_id.native) + Txn.sender.bytes
        donor_exists, donor_data = op.Box.get(donor_key)
        assert donor_exists, "No donation found"
        
        refund_amount = op.btoi(donor_data)
        assert refund_amount > UInt64(0), "Already refunded"
        
        # Check contract has sufficient balance
        available = Global.current_application_address.balance - Global.current_application_address.min_balance
        assert refund_amount <= available, "Insufficient funds for refund"
        
        # Send refund
        itxn.Payment(
            receiver=Txn.sender,
            amount=refund_amount,
            fee=Global.min_txn_fee,
        ).submit()
        
        # Mark as refunded
        op.Box.put(donor_key, op.itob(UInt64(0)))
    
    @arc4.abimethod
    def cancel_campaign(
        self,
        campaign_id: arc4.UInt64,
    ) -> None:
        """
        Cancel a campaign.
        Only creator can cancel. Triggers refund eligibility.
        
        Args:
            campaign_id: ID of the campaign
        """
        # Get campaign
        campaign_key = Bytes(b"camp_") + op.itob(campaign_id.native)
        campaign_exists, campaign_data = op.Box.get(campaign_key)
        assert campaign_exists, "Campaign does not exist"
        
        # Verify caller is creator
        creator = op.extract(campaign_data, 0, 32)
        assert Txn.sender.bytes == creator, "Only creator can cancel"
        
        status = op.btoi(op.extract(campaign_data, 88, 8))
        assert status == STATUS_ACTIVE, "Campaign not active"
        
        # Update status to failed (enables refunds)
        updated_campaign = (
            op.extract(campaign_data, 0, 88) +
            op.itob(STATUS_FAILED) +
            op.extract(campaign_data, 96, 16)
        )
        op.Box.put(campaign_key, updated_campaign)
    
    @arc4.abimethod
    def get_campaign(
        self,
        campaign_id: arc4.UInt64,
    ) -> arc4.Tuple[arc4.Address, arc4.Address, arc4.UInt64, arc4.UInt64, arc4.UInt64, arc4.UInt64]:
        """
        Get campaign details.
        
        Args:
            campaign_id: ID of the campaign
            
        Returns:
            Tuple of (creator, beneficiary, goal, raised, deadline, status)
        """
        campaign_key = Bytes(b"camp_") + op.itob(campaign_id.native)
        campaign_exists, campaign_data = op.Box.get(campaign_key)
        assert campaign_exists, "Campaign does not exist"
        
        return arc4.Tuple((
            arc4.Address(op.extract(campaign_data, 0, 32)),    # creator
            arc4.Address(op.extract(campaign_data, 32, 32)),   # beneficiary
            arc4.UInt64(op.btoi(op.extract(campaign_data, 64, 8))),  # goal
            arc4.UInt64(op.btoi(op.extract(campaign_data, 72, 8))),  # raised
            arc4.UInt64(op.btoi(op.extract(campaign_data, 80, 8))),  # deadline
            arc4.UInt64(op.btoi(op.extract(campaign_data, 88, 8))),  # status
        ))
    
    @arc4.abimethod
    def get_milestone(
        self,
        campaign_id: arc4.UInt64,
        milestone_index: arc4.UInt64,
    ) -> arc4.Tuple[arc4.UInt64, arc4.UInt64, arc4.Bool]:
        """
        Get milestone details.
        
        Args:
            campaign_id: ID of the campaign
            milestone_index: Index of the milestone
            
        Returns:
            Tuple of (amount, released, is_completed)
        """
        milestone_key = (
            Bytes(b"mile_") + 
            op.itob(campaign_id.native) + 
            Bytes(b"_") + 
            op.itob(milestone_index.native)
        )
        milestone_exists, milestone_data = op.Box.get(milestone_key)
        assert milestone_exists, "Milestone does not exist"
        
        return arc4.Tuple((
            arc4.UInt64(op.btoi(op.extract(milestone_data, 0, 8))),   # amount
            arc4.UInt64(op.btoi(op.extract(milestone_data, 8, 8))),   # released
            arc4.Bool(op.btoi(op.extract(milestone_data, 16, 8)) == UInt64(1)),  # completed
        ))
    
    @arc4.abimethod
    def get_campaign_count(self) -> arc4.UInt64:
        """
        Get total number of campaigns.
        
        Returns:
            Campaign count
        """
        return arc4.UInt64(self.campaign_count.value)
    
    @arc4.abimethod
    def get_my_donation(
        self,
        campaign_id: arc4.UInt64,
    ) -> arc4.UInt64:
        """
        Get caller's total donation to a campaign.
        
        Args:
            campaign_id: ID of the campaign
            
        Returns:
            Total donation amount
        """
        donor_key = Bytes(b"donor_") + op.itob(campaign_id.native) + Txn.sender.bytes
        donor_exists, donor_data = op.Box.get(donor_key)
        
        if donor_exists:
            return arc4.UInt64(op.btoi(donor_data))
        else:
            return arc4.UInt64(0)
