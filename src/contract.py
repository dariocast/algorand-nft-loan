from pyteal import *
from beaker import *
from typing import Final


class BorrowMyNFT(Application):
    nft_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="A handle to retrieve the correct NFT",
    )
    borrower_address: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="The address of the borrower",
    )
    lender_address: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Current highest bidder",
    )
    highest_bid: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Highest bid",
    )
    auction_base: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Auction starting amount",
    )
    auction_period: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Auction deadline block number",
    )
    payback_deadline: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Loan Deadline (initially stores the duration, the deadline is calculated after AcceptOffer is invoked",
    )
    last_interest_update_block: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="starting block to compute the interest. It stores the block corresponding to the last successful "
              "invocation of pay_back",
    )
    debt_left: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="The current debt. debt_left=debt_left*(1+interset_rate*(current_block - last_interest_update_block))",
    )

    # 0=initial state, 1=set_offer invoked, 2 = acceptBid invoked,
    state: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="The current contract state",
    )

    # Contract address minimum balance
    MIN_BAL = Int(100000)

    # Algorand minimum txn fee
    FEE = Global.min_txn_fee()

    # 1 block every 4 seconds => 7776000 bloks/year
    # if we put 10% interest rate, we get 0.000001286 per block (0.000001 by approximation).
    # thus interest rate = 1/1000000
    # INTEREST_RATE_NUM = Int(1) <- does not affect multiplications, we can ignore it
    INTEREST_RATE_DEN = Int(1000000)

    # Similarly, we set the contract creator interest rate (around 1% per loan)
    INTEREST_RATE_CONTRACT_DEN = Int(100)

    # 10 years
    MAX_PAYBACK_DEADLINE = Int(77760000)

    # 1 month
    MAX_AUCTION_PERIOD = Int(216000)

    # A maximum loan must be specified to avoid overflows when calculating the interest ( 2*10e11 microalgos)
    MAX_N_ALGOS = Int(200000000000)

    @create
    def create(self):
        """Deploys the contract and intialize app states"""
        return self.initialize_application_state()

    @delete(authorize=Authorize.only(Global.creator_address()))
    def delete(self):
        """Enable deletion only if state is 0 = initial"""
        return Seq(
            Assert(
                self.state == Int(0),
                Balance(self.address) != Int(0),
            ),
            self.pay_me_internal(),
        )

    # Add an external method with ABI method signature `health(string)string`
    @external
    def health(self, *, output: abi.String):
        """Returns the contract health"""
        return output.set(
            Bytes("Contract is up and running!")
        )
    # Reset state is used to reset state variables to their default values
    @internal
    def reset_state(self):
        return Seq(
            self.state.set(Int(0)),
            self.debt_left.set(Int(0)),
            self.last_interest_update_block.set(Int(0)),
            self.payback_deadline.set(Int(0)),
            self.auction_period.set(Int(0)),
            self.auction_base.set(Int(0)),
            self.highest_bid.set(Int(0)),
            self.lender_address.set(Bytes("")),
            self.borrower_address.set(Bytes("")),
            self.nft_id.set(Int(0)),
        )

    #pay_me_internal is used by both pay_me and delete. pay_me_internal pays the contract owner by emptying the contract balance. 
    @internal
    def pay_me_internal(self):
        return Seq(
            Assert(
                Txn.fee() >= Global.min_txn_fee() * Int(2),
                self.state.get() != Int(1),
            ),
            InnerTxnBuilder.Execute({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: Txn.sender(),
                TxnField.amount: Balance(self.address) - MinBalance(self.address),
                TxnField.fee: Int(0)
            })
        )
    #pay_me is a wrapper around pay_me_internal. 
    @external(authorize=Authorize.only(Global.creator_address()))
    def pay_me(self):
        return Seq(
            Assert(
                Balance(self.address) > MinBalance(self.address)
            ),
            self.pay_me_internal()
        )

    # 2 transactions are needed: one to transfer algo and increase the contract balance (the contract minimum balance
    # must be sufficient to accept the nft), one to optin. provide_access_to_nft handles the optin logic.

    @external
    def provide_access_to_nft(self, nft: abi.Asset, payment: abi.PaymentTransaction):
        return Seq(
            Assert(
                Global.group_size() == Int(2),
                Txn.fee() >= self.FEE * Int(3),
                payment.get().receiver() == self.address,
                payment.get().amount() >= self.MIN_BAL,
            ),
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: nft.asset_id(),
                    TxnField.asset_receiver: self.address,
                    TxnField.fee: Int(0),
                    TxnField.asset_amount: Int(0),
                }
            ),
            self.initialize_account_state(),
        )

    # 2 transactions are checked:
    # one to transfer the NFT, 
    # and the one calling set_offer
    # Borrowers can call set_offer to auction their NFTs
    @external
    def set_offer(
            self,
            asset_xfer: abi.AssetTransferTransaction,
            auction_base: abi.Uint64,
            auction_period: abi.Uint64,
            payback_deadline: abi.Uint64
    ):
        asset_holding = AssetHolding.balance(
            Global.current_application_address(), asset_xfer.get().xfer_asset()
        )
        asset_manager = AssetParam.manager(Int(0))
        asset_clawback = AssetParam.clawback(Int(0))
        asset_freeze = AssetParam.freeze(Int(0))
        return Seq(
            asset_holding,
            asset_manager,
            asset_clawback,
            asset_freeze,
            Assert(
                Global.group_size() == Int(2),
                # check asset transfer is correct
                asset_xfer.get().asset_receiver() == self.address,
                asset_xfer.get().asset_amount() == Int(1),
                asset_xfer.get().sender() == Txn.sender(),
                # check NFT has no dangerous fields set
                Txn.assets[0] == asset_xfer.get().xfer_asset(),      
                asset_manager.value()==Global.zero_address(),  
                asset_clawback.value()==Global.zero_address(), 
                asset_freeze.value()==Global.zero_address(), 
                # check state correctness
                self.state.get() == Int(0),
                # checking inputs
                auction_base.get() > Int(0),
                auction_base.get() < self.MAX_N_ALGOS,
                auction_period.get() > Int(0),
                auction_period.get() < self.MAX_AUCTION_PERIOD,
                # payback now is the number of round into which borrower must pay after accepting loan
                payback_deadline.get() > Int(0),
                payback_deadline.get() < self.MAX_PAYBACK_DEADLINE,
            ),
            #updatig contract state
            self.state.set(Int(1)),
            self.nft_id.set(asset_xfer.get().xfer_asset()),
            self.auction_base.set(auction_base.get()),
            self.auction_period.set(Global.round()+auction_period.get()),
            self.payback_deadline.set(payback_deadline.get()),
            self.borrower_address.set(Txn.sender())
        ) 

    #Place bid isused by the lender to bis for the NFT
    @external
    def place_bid(self, payment: abi.PaymentTransaction):
        return Seq(
            Assert(
            	Global.group_size() == Int(2),	
                Txn.fee() >= Global.min_txn_fee() * Int(3),	
                self.state.get() == Int(1),	
                payment.get().receiver() == self.address,	
                payment.get().amount() > self.highest_bid.get(),	
                payment.get().amount() > self.auction_base.get(),	
                payment.get().amount() <= self.MAX_N_ALGOS,	
                Global.round() <= self.auction_period.get()	
            ),
            If(self.highest_bid.get() > Int(0)).Then(Seq(
                InnerTxnBuilder.Execute(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.amount: self.highest_bid.get(),
                        TxnField.receiver: self.lender_address.get(),
                        TxnField.fee: Int(0)
                    })
            )),
            self.highest_bid.set(payment.get().amount()),
            self.lender_address.set(payment.get().sender())
        )

    #Accept bid is used by the borrower to take the loan
    @external
    def accept_bid(self):
        return Seq(
            Assert(
                Txn.fee() >= Global.min_txn_fee() * Int(2),
                Txn.sender() == self.borrower_address.get(),
                self.highest_bid.get() > Int(0),
                self.state.get() == Int(1),
            ),
            self.state.set(Int(2)),
            self.debt_left.set(self.highest_bid.get()),
            self.last_interest_update_block.set(Global.round()),
            self.payback_deadline.set(Add(Global.round(), self.payback_deadline.get())),
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.amount: Minus(self.highest_bid.get(), Div(self.highest_bid.get(), self.INTEREST_RATE_CONTRACT_DEN)),
                    TxnField.receiver: self.borrower_address.get(),
                    TxnField.fee: Int(0)
                })
        )

    #if the auction period expires and no offer was accepted, the lender may decide to call timeout and return the contract holdings to their original owners
    @external
    def timeout(self):
        return Seq(
            Assert(
                Txn.fee() >= Global.min_txn_fee()*Int(3),	
                self.state.get() == Int(1),	
                Global.round() > self.auction_period.get()
            ),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: self.nft_id.get(),
                    TxnField.asset_amount: Int(1),
                    TxnField.asset_receiver: self.borrower_address.get(),
                    TxnField.asset_close_to: self.borrower_address.get(),
                    TxnField.fee: Int(0)
                }),
            If(self.highest_bid > Int(0)).Then(Seq(
                InnerTxnBuilder.Next(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.amount: self.highest_bid.get(),
                        TxnField.receiver: self.lender_address.get(),
                        TxnField.fee: Int(0)
                    })
            )),
            InnerTxnBuilder.Submit(),
            self.reset_state()
        )
    #If the bids are low, the borower may decide to keep the NFT instead of accepting the loan
    @external
    def cancel_offer(self):
        return Seq(
            Assert(
                Txn.sender() == self.borrower_address.get(),
                self.state.get() == Int(1),
                Txn.fee() >= Global.min_txn_fee() * Int(3),
            ),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: self.nft_id.get(),
                    TxnField.asset_receiver: self.borrower_address.get(),
                    TxnField.asset_close_to: self.borrower_address.get(),
                    TxnField.fee: Int(0),
                }
            ),
            If(Gt(self.highest_bid, Int(0))).Then(Seq(
                InnerTxnBuilder.Next(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.amount: self.highest_bid.get(),
                        TxnField.receiver: self.lender_address.get(),
                        TxnField.fee: Int(0)
                    }),
            )),
            InnerTxnBuilder.Submit(),
            self.reset_state()
        )

    #After accepting the loan, the borrower uses pay_back to pay the loan back. The loan can be repayed in multiple payments
    @external
    def pay_back(self, payment: abi.PaymentTransaction):
        # interest=debt_left*INTEREST_RATE_NUM*blocks/INTEREST_RATE_DEN. Notice: INTEREST_RATE_NUM=1
        interest = Div(Mul(self.debt_left.get(), Minus(Global.round(), self.last_interest_update_block.get())),
                       self.INTEREST_RATE_DEN)
        return Seq(
            Assert(
                Global.group_size() == Int(2),	
                Txn.fee() >= Global.min_txn_fee() * Int(5),	
                self.state.get() == Int(2),	
                payment.get().receiver() == self.address,	
                payment.get().amount() >= interest
            ),
            self.debt_left.set(self.debt_left.get() + interest),
            self.last_interest_update_block.set(Global.round()),
            #the borrower sent too many algos
            If(payment.get().amount() > self.debt_left.get()).Then(Seq(
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.amount: payment.get().amount() - self.debt_left.get(),
                        TxnField.receiver: Txn.sender(),
                        TxnField.fee: Int(0)
                    }),
                InnerTxnBuilder.Next(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.amount: self.debt_left.get(),
                        TxnField.receiver: self.lender_address.get(),
                        TxnField.fee: Int(0)
                    }),
                InnerTxnBuilder.Next(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.AssetTransfer,
                        TxnField.xfer_asset: self.nft_id.get(),
                        TxnField.asset_amount: Int(1),
                        TxnField.asset_receiver: self.borrower_address.get(),
                        TxnField.asset_close_to: self.borrower_address.get(),
                        TxnField.fee: Int(0)
                    }),
                InnerTxnBuilder.Submit(),
                self.reset_state()
            #the borrower sent the perfect amount of algos    
            )).ElseIf(payment.get().amount() == self.debt_left.get()).Then(Seq(
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.amount: self.debt_left.get(),
                        TxnField.receiver: self.lender_address.get(),
                        TxnField.fee: Int(0)
                    }),
                InnerTxnBuilder.Next(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.AssetTransfer,
                        TxnField.xfer_asset: self.nft_id.get(),
                        TxnField.asset_amount: Int(1),
                        TxnField.asset_receiver: self.borrower_address.get(),
                        TxnField.asset_close_to: self.borrower_address.get(),
                        TxnField.fee: Int(0)
                    }),
                InnerTxnBuilder.Submit(),
                self.reset_state()
            #the borrower paid back a portion of the loan    
            )).Else(Seq(
                InnerTxnBuilder.Execute({
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.amount: payment.get().amount(),
                    TxnField.receiver: self.lender_address.get(),
                    TxnField.fee: Int(0)
                }),
                self.debt_left.set(self.debt_left.get() - payment.get().amount())
            ))
        )
    #if the payback period expires, the lender can obtain the NFT
    @external
    def loan_expired(self):
        return Seq(
            Assert(
                Txn.sender() == self.lender_address.get(),
                Txn.fee() >= Global.min_txn_fee() * Int(2),
                self.state.get() == Int(2),
                Global.round() >= self.payback_deadline.get()
            ),
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: self.nft_id.get(),
                    TxnField.asset_amount: Int(1),
                    TxnField.asset_receiver: self.lender_address.get(),
                    TxnField.asset_close_to: self.lender_address.get(),
                    TxnField.fee: Int(0)
                }),
            self.reset_state()
        )

      
    #utility to access the contract state
    @external(read_only=True)
    def read_state(self, *, output: abi.Uint64):
        """Read current state."""
        return output.set(self.state)


#utility to write the teal code to file for debugging purposes
if __name__ == "__main__":
    import os
    import json

    path = os.path.dirname(os.path.abspath(__file__))

    app = BorrowMyNFT()

    # Dump the contract as json
    with open(os.path.join(path, "contract.json"), "w") as f:
        f.write(json.dumps(app.application_spec(), indent=2))

    # Dump the contract as approval and clear TEAL
    with open(os.path.join(path, "approval.teal"), "w") as f:
        f.write(app.approval_program)
    with open(os.path.join(path, "clear.teal"), "w") as f:
        f.write(app.clear_program)
