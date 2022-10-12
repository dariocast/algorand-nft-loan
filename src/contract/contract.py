from src.utils.accounts import *
from pyteal import *
from beaker import *
from typing import Final
from algosdk.future import transaction

# Create a class, subclassing Application from beaker
class HelloBeaker(Application):

    nft_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="A handle to retrieve the correct NFT",
    )
    borrower_address: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="The address of the borrower",
    )
    lender_address: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Current bidder",
    )
    n_algos: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Highest bid",
    )
    loan_threshold: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Auction starting amount",
    )
    auction_period: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Auction deadline block number",
    )
    payback_deadline: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Loan Deadline (initially stores the duration, the deadline is calculated after AcceptOffer is invoked",
    )
    last_interest_update_block: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="starting block to compute the interest. It stores the block corresponding to the last successful invocation of PayBack",
    )
    debt_left: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="The current debt. debt_left=debt_left*((1+interset_rate)^(current_block - last_interest_update_block",
    )

    #0=initial state, 1=offer invoked, 2 = acceptBid invoked,  
    state: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="The current debt. debt_left=debt_left*((1+interset_rate)^(current_block - last_interest_update_block",
    )

    @create
    def create(self):
        return self.initialize_application_state()


    @internal   
    def ResetState (self):
        return Seq(
            self.state.set(Int(0)),
            self.debt_left.set(Int(0)),
            self.last_interest_update_block.set(int(0)),
            self.payback_deadline.set(Int(0)),
            self.auction_period.set(Int(0)),
            self.loan_threshold.set(Int(0)),
            self.n_algos.set(Int(0)),
            self.lender_address.set(Bytes("")),
            self.borrower_address.set(Bytes("")),
            self.nft_id.set(Bytes(""))
        )  

    @external(authorize=Authorize.only(Global.creator_address()))
    def PayMe(self, receiver: abi.Account):
        return InnerTxnBuilder.Execute({
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: Minus(Balance(Global.current_application_address()), Add(MinBalance(Global.current_application_address()), Global.min_txn_fee())),
            TxnField.receiver: receiver.address(),
            TxnField.fee: Global.min_txn_fee()
        })

    #2 transactions are needed:
    # one to transfer algo and increase the contract balance (the contract minimum balance must be sufficiet to accept the nft),
    # one to Optin

    @external    
    def Optin (self, nft: abi.Asset):
        return Seq(
            Assert(Ge(Txn.fee(), Mul(Global.min_txn_fee(), Int(2)))),
            #check the other tranaction exists and sends algo to this account
            InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: nft.asset_id(),
                TxnField.asset_receiver: self.address,
                TxnField.fee: Int(0),
                TxnField.asset_amount: Int(0),
            }
        )
        )


    #2 transactions are needed:
    # one to transfer the NFT, 
    # and the one calling Offer
    @external    
    def Offer (self, nft: abi.Asset, loan_threshold: abi.Uint64, auction_period:abi.Uint64, payback_deadline:abi.Uint64):
        return Seq(
            Assert(Eq(self.state, Int(0))),
            Assert(Ge(loan_threshold, )),
            Assert(Le(loan_threshold, )),
            Assert(Ge(auction_period, )),
            Assert(Le(auction_period, )),
            Assert(Ge(payback_deadline, )),
            Assert(Le(payback_deadline, )),
            #Assert(Txn.sender()=nft.sender())
            #Assert(nft.AssetReceiver, self.address)
            #ManagerAddr, FreezeAddr, ClawbackAddr of the asset must be null
            #AssetAmount must be 1

            self.state.set(Int(1)),
            self.loan_threshold.set(loan_threshold),
            self.auction_period.set(Add(Global.round(), auction_period)),
            self.payback_deadline.set(payback_deadline),
            self.nft_id.set(nft.asset_id()),
            self.borrower_address.set(Txn.sender())
        )


    #2 transactions are needed:
    # one to transfer the n_algos, 
    # one calling Bid
    #@external    
    #def Bid (n_algos: abi.Uint64):
       # lender_address=tx.sender; n_algos=?????
       #pass 

    @external    
    def AcceptBid (self):
        return Seq(
            Assert(Ge(Txn.fee(), Mul(Global.min_txn_fee(), Int(2)))),
            Assert(Eq(Txn.sender(), self.borrower_address)),
            Assert(Gt(self.n_algos, Int(0))),
            self.state.set(Int(2)),
            self.debt_left.set(self.n_algos),
            self.last_interest_update_block.set(Global.round()),
            self.payback_deadline.set(Add(Global.round(), self.payback_deadline)),
            InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.amount: self.n_algos,
                TxnField.receiver: self.borrower_address,
                TxnField.fee: Int(0)
            })
        )

    @external    
    def Timeout (self):
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
            If(Gt(self.n_algos, Int(0))).Then(
                InnerTxnBuilder.Next(),
                InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.amount: self.n_algos,
                    TxnField.receiver: self.lender_address,
                    TxnField.fee: Int(0)
                })
            ),
            InnerTxnBuilder.Submit(),
            self.ResetState()
        )    

    
    @external   
    def CancelOffer (self):
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
            If(Gt(self.n_algos, Int(0))).Then(
                InnerTxnBuilder.Next(),
                InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.amount: self.n_algos,
                    TxnField.receiver: self.lender_address,
                    TxnField.fee: Int(0)
                })
            ),
            InnerTxnBuilder.Submit(),
            self.ResetState()
        )  
    #2 transactions are needed:
    # one to transfer m_algos, 
    # one calling PayBack
    #@external    
    #def PayBack (m_algos:abi.Uint64):
       #current_block = ????Global.block+1 ; m_algos=?????
       #pass

    @external    
    def LoanExpires (self):
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
            self.ResetState()
        )      

    # Add an external method with ABI method signature `hello(string)string`
    @external
    def hello(self, name: abi.String, *, output: abi.String):
        # Set output to the result of `Hello, `+name
        return output.set(Concat(Bytes("Hello, "), name.get()))


def demo():


    # Create an Application client
    
    acc=[s for s in sandbox.get_accounts() if s.address == get_default_algorand_keypair()[1]].pop()
    app_client = client.ApplicationClient(
        # Get sandbox algod client
        client=sandbox.get_algod_client(),
        # Instantiate app with the program version (default is MAX_TEAL_VERSION)
        app=HelloBeaker(version=6),
        # Get acct from sandbox and pass the signer
        signer=acc.signer #pop().signer,
    )

    # Deploy the app on-chain
    app_id, app_addr, txid = app_client.create()
    print(
        f"""Deployed app in txid {txid}
        App ID: {app_id} 
        Address: {app_addr} 
    """
    )
    print(app_client.client.account_info(acc.address).get('amount'))
    app_client.fund(5 * consts.algo)
    print(app_client.client.account_info(acc.address).get('amount'))
    result=app_client.call(HelloBeaker.PayMe, receiver=acc.address)
    print(result.return_value, result.decode_error)
    print((app_client.client.account_info(acc.address)).get('amount'))
    print(acc.address)
    #params = app_client.get_suggested_params() 
    #receiver=app_client.get_application_account_info().address
    #note = "Hello World".encode()
    #amount = 1000000
    #unsigned_txn = transaction.PaymentTxn(app_client.get_sender(), params, receiver, amount, None, note)
    #signed_txn=unsigned_txn.sign(acc.private_key)
    #txid = app_client.send_transaction(signed_txn)
    #print("Successfully sent transaction with txID: {}".format(txid))
    #try:
    #    confirmed_txn = transaction.wait_for_confirmation(app_client, txid, 4)  

    #except Exception as err:
    #    print(err)
    #    return




if __name__ == "__main__":
    demo()