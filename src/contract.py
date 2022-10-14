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
    loan_threshold: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Auction starting amount",
    )
    auction_period: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        # 1 day = 86400 seconds, 1 block = 5 seconds, 1 day = 17280 blocks
        default=Int(17280),
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
        descr="The current debt. debt_left=debt_left*((1+interset_rate)^(current_block - last_interest_update_block",
    )

    # 0=initial state, 1=set_offer invoked, 2 = acceptBid invoked,
    state: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="The current contract state",
    )

    # Contract address minimum balance
    MIN_BAL = Int(100000)

    # Algorand minimum txn fee
    FEE = Int(1000)

    @create
    def create(self):
        """Deploys the contract and intialize app states"""
        return self.initialize_application_state()

    @delete(authorize=Authorize.only(Global.creator_address()))
    def delete(self):
        """Enable deletion only if state is 0 = initial"""
        return Seq(
            Assert(self.state == Int(0)),
            If(
                Balance(self.address) > (self.MIN_BAL + self.FEE),
                self.pay_me_internal(),
            ),
        )

    # Add an external method with ABI method signature `hello(string)string`
    @external
    def health(self, *, output: abi.String):
        # Set output to the result of `Hello, `+name
        return output.set(
            Bytes(
                f"Contract {Global.current_application_id()} is up and running"
            )
        )

    @internal
    def reset_state(self):
        return Seq(
            self.state.set(Int(0)),
            self.debt_left.set(Int(0)),
            self.last_interest_update_block.set(Int(0)),
            self.payback_deadline.set(Int(0)),
            self.auction_period.set(Int(0)),
            self.loan_threshold.set(Int(0)),
            self.highest_bid.set(Int(0)),
            self.lender_address.set(Bytes("")),
            self.borrower_address.set(Bytes("")),
            self.nft_id.set(Int(0)),
        )

    @internal
    def pay_me_internal(self):
        app_balance = Balance(self.address)
        return Seq(
            Assert(
                app_balance > (self.MIN_BAL + self.FEE)
            ),
            InnerTxnBuilder.Execute({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: Txn.sender(),
                TxnField.amount: app_balance - (self.MIN_BAL + self.FEE),
            })
        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def pay_me(self):
        return self.pay_me_internal()

    # To be called from borrower to trigger the NFT optin to the contract
    # this must be in a group of 3 transactions: [app_call, asset_xfer, app_call]
    @external
    def provide_access_to_nft(self, nft_id: abi.Uint64):
        return Seq(
            Assert(
                self.state == Int(0),
                Global.group_size() == Int(3),
                Txn.fee() >= self.FEE * Int(2),
            ),
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: nft_id.get(),
                    TxnField.asset_receiver: self.address,
                    TxnField.fee: Int(0),
                    TxnField.asset_amount: Int(0),
                }
            ),
            self.nft_id.set(nft_id.get()),
            self.state.set(Int(1))
        )

    # 2 transactions are checked:
    # one to transfer the NFT, 
    # and the one calling set_offer
    @external
    def set_offer(
            self,
            asset_xfer: abi.AssetTransferTransaction,
            loan_threshold: abi.Uint64,
            auction_period: abi.Uint64,
            payback_deadline: abi.Uint64
    ):
        return Seq(
            Assert(
                Global.group_size() == Int(3),
                # check asset transfer is correct
                asset_xfer.get().asset_receiver() == self.address,
                asset_xfer.get().xfer_asset() == self.nft_id.get(),
                asset_xfer.get().asset_amount() == Int(1),
                asset_xfer.get().asset_sender() == Txn.sender(),
                self.state.get() == Int(0),
                # TODO following conditions to be defined
                # self.loan_threshold.get() > Int(0),
            ),
            # Assert(Eq(self.state, Int(0))),
            # Assert(Ge(loan_threshold, )),
            # Assert(Le(loan_threshold, )),
            # Assert(Ge(auction_period, )),
            # Assert(Le(auction_period, )),
            # Assert(Ge(payback_deadline, )),
            # Assert(Le(payback_deadline, )),
            # Assert(Txn.sender()=nft.sender())
            # Assert(nft.AssetReceiver, self.address)
            # ManagerAddr, FreezeAddr, ClawbackAddr of the asset must be null
            # AssetAmount must be 1

            self.state.set(Int(1)),
            self.loan_threshold.set(loan_threshold.get()),
            self.auction_period.set(Add(Global.round(), auction_period.get())),
            self.payback_deadline.set(payback_deadline.get()),
            self.borrower_address.set(Txn.sender())
        )

    # 2 transactions are needed:
    # one to transfer the highest_bid, 
    # one calling place_bid
    # @external
    # def place_bid (highest_bid: abi.Uint64):
    # lender_address=tx.sender; highest_bid=?????
    # pass

    @external
    def accept_bid(self):
        return Seq(
            Assert(Ge(Txn.fee(), Mul(Global.min_txn_fee(), Int(2)))),
            Assert(Eq(Txn.sender(), self.borrower_address)),
            Assert(Gt(self.highest_bid, Int(0))),
            self.state.set(Int(2)),
            self.debt_left.set(self.highest_bid),
            self.last_interest_update_block.set(Global.round()),
            self.payback_deadline.set(Add(Global.round(), self.payback_deadline)),
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.amount: self.highest_bid,
                    TxnField.receiver: self.borrower_address,
                    TxnField.fee: Int(0)
                })
        )

    @external
    def timeout(self):
        return Seq(
            Assert(Ge(Txn.fee(), Mul(Global.min_txn_fee(), Int(3)))),
            Assert(Eq(self.state, Int(1))),
            Assert(Gt(Global.round(), self.auction_period)),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: self.nft_id,
                    TxnField.asset_amount: Int(1),
                    TxnField.asset_receiver: self.borrower_address,
                    TxnField.fee: Int(0)
                }),
            If(Gt(self.highest_bid, Int(0))).Then(
                InnerTxnBuilder.Next(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.amount: self.highest_bid,
                        TxnField.receiver: self.lender_address,
                        TxnField.fee: Int(0)
                    })
            ),
            InnerTxnBuilder.Submit(),
            self.reset_state()
        )

    @external
    def cancel_offer(self):
        return Seq(
            Assert(Eq(Txn.sender(), self.borrower_address)),
            Assert(Ge(Txn.fee(), Mul(Global.min_txn_fee(), Int(3)))),
            Assert(Eq(self.state, Int(1))),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: self.nft_id,
                    TxnField.asset_amount: Int(1),
                    TxnField.asset_receiver: self.borrower_address,
                    TxnField.fee: Int(0)
                }
            ),
            If(Gt(self.highest_bid, Int(0))).Then(
                InnerTxnBuilder.Next(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.amount: self.highest_bid,
                        TxnField.receiver: self.lender_address,
                        TxnField.fee: Int(0)
                    })
            ),
            InnerTxnBuilder.Submit(),
            self.reset_state()
        )

    # 2 transactions are needed:
    # one to transfer m_algos,
    # one calling pay_back
    # @external
    # def pay_back (m_algos:abi.Uint64):
    # current_block = ????Global.block+1 ; m_algos=?????
    # pass
    @external
    def loan_expired(self):
        return Seq(
            Assert(Eq(Txn.sender(), self.lender_address)),
            Assert(Ge(Txn.fee(), Mul(Global.min_txn_fee(), Int(2)))),
            Assert(Eq(self.state, Int(2))),
            Assert(Gt(Global.round(), self.payback_deadline)),
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: self.nft_id,
                    TxnField.asset_amount: Int(1),
                    TxnField.asset_receiver: self.lender_address,
                    TxnField.fee: Int(0)
                }),
            self.reset_state()
        )

        # Add an external method with ABI method signature `hello(string)string`

    @external(read_only=True)
    def read_state(self, *, output: abi.Uint64):
        """Read amount of RSVP to the event. Only callable by Creator."""
        return output.set(self.state)

    @external
    def hello(self, name: abi.String, *, output: abi.String):
        # Set output to the result of `Hello, `+name
        return output.set(Concat(Bytes("Hello, "), name.get()))


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
