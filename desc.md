# Introduction

Digitization, standardization, decentralization, resiliency, and verifiability are some of the main blockchain adoption drivers, as they allow revolutionizing existing processes by making such processes more secure and efficient. This solution provides a glimpse of the endless possibilities offered by Algorand by describing a simplified digital pawnshop.

In our scenario, the borrower (B) uses a non-fungible token (NFT) as collateral to obtain a loan in Algos. In particular, B auctions the NFT and receives some bids from the lenders. If B accepts the highest offer, then a loan is established between B and the highest bidder (L): B receives the loan from L and can pay it back (interest included) within a fixed period. If B does not pay the loan back, L keeps the NFT. B and L do not need to trust each other, as their interaction is mediated and secured by a smart contract. The smart contract is created and initialized by the Contract Owner (CO), which receives a small fee each time a loan is emitted through the smart contract.

Notice: the solution was developed in the context of the  [International School on Algorand smart Contracts](https://algorand-school.github.io/algorand-school) and won the second prize. Nonetheless, the code is not production ready (there might be bugs), and better/smarter ways of implementing the solution may exist.

The code is available on [Github](https://github.com/dariocast/algorand-nft-loan).

# Before we start
This section describes how pawnshops work, the benefits of creating a digital pawnshop in Algorand, the tools we used, and which challenges we faced. You may skip this section if you are only interested in the code discussion.

## Physical pawnshops
Physical pawnshops have an interesting business model: pawnshops offer loans to their users in exchange for an item more valuable than the loan. If the user pays the loan back within an agreed time, the user can take back the item. Otherwise, the pawnshop keeps the item and tries to sell it to recover the loss.

We highlight some of the main challenges of physical pawnshops: 

* The pawnshop and the user must agree on the evaluation of the item. In particular, some items may be difficult to sell or have high volatility.  
* The pawnshop must check that the item is not fake/stolen.
* The user must trust the pawnshop (which could sell the item before the deadline, damage it, etc.)


## Goal
Our goal is to implement a lending protocol based on NFTs. The vast majority of DeFi lending protocols use fungible tokens as collateral, which can be liquidated to pay back the lender. However, NFTs are less liquid and more volatile than fungible tokens. Thus, different strategies must be employed when handling NFTs. To this extent, our solution is inspired by physical pawnshops, as described in the introduction.

The digital pawnshop tries to solve the main challenges of physical pawnshops.


* We use an auction protocol to obtain a fair evaluation of the loan price of the asset without introducing trusted third parties (e.g., oracles).
* The transparency and verifiability of the Algorand blockchain guarantee the authenticity and ownership of the asset.
* The interaction between B and L is mediated by the smart contract, guaranteeing the automatic and tamper-resilient management of the loan process (if the smart contract is coded correctly, no party can cheat).


The solution is profitable for all the users that are involved.



* B obtains a loan.
* L has an interest on the loaned Algos and obtains the NFT in case B is not able to pay the loan back.
* CO gains a fee on each loan processed by the smart contract.

## Challenges
The main challenges are related to the limits that Algorand imposes on smart contracts to make the network secure and efficient.


* Smart contract storage is limited—Our smart contract is not affected by such a limitation as it handles a single loan at a time, but such a limitation is something to consider when scaling the application up.
* There are only two data types: unsigned integers and fixed-size byte arrays—We do not need dynamic arrays as we manage a single loan at a time, but a real pawn shop would handle a varying number of loans in parallel. Thus, a parent contract handling the creation and destruction of secondary contracts should be added to obtain a more realistic implementation.
* The contract needs to send inner transactions but cannot pay for their fees—Our solution manages this aspect.
* Any Algorand Standard Asset can be received as collateral—An Algorand account can receive an asset only after the account opts in for such an asset. Moreover, each opted-in asset increases the minimum balance of the account. Our solution manages the dynamic minimum balance and the opt-in logic. However, additional checks should be added to the current implementation (e.g., checking if the borrower can receive the NFT before sending it back).
* Atomic groups (i.e., transactions that must be committed altogether or none at all) must be handled.
* B must be able to pay the loan back in any percentage and in any number of payments. The interest must be computed correctly and only on the portion of the loan that is yet to be paid—We implemented the logic, but further testing is required on this aspect.

## Tools
We used the following tools:


* [the Algorand sandbox]( https://github.com/algorand/sandbox), which allows testing the smart contract locally;
* [Beaker](https://algorand-devrel.github.io/beaker/html/index.html), a PyTeal-based framework for smart contract development in Algorand.


# Smart contract description
This section describes how the smart contract handles the transactions received by B, L, and CO. The smart contract is stateful and uses the contract state to keep track of the relevant information. Some information could be moved to the account state of B/L to improve the cost efficiency of the contract, but we preferred to avoid such an option, as the account state can be deleted by its owner (B/L) at will. Thus, the smart contract should be designed to be unaffected by such a deletion that may happen at any moment. 

## Contract state
The contract state stores the following information:


* `nft_id` is a handle to retrieve the correct NFT;
* `borrower_address` is the address of B;
* `lender_address` is the address of the current highest bidder;
* `highest_bid` is the highest bid value (in Algos);
* `auction_base` is the auction starting amount;
* `auction_period` is the auction deadline block number. The client submits a duration, and the contract uses it and the current block to compute the deadline;
* `payback_deadline` is the loan payback deadline. `payback_deadline` initially stores the duration. After `accept_offer()` is invoked, the deadline is computed.
* `last_interest_update_block` stores the block corresponding to the last successful invocation of `pay_back()`. `last_interest_update_block` is used to compute the interest.
* `debt_left` is the debt that B must still pay back.
* `state` is used to track the current contract state and simplify the execution logic.

##Transaction handling
This section describes how the smart contract processes user transactions. It is possible to interact with the smart contract by invoking the methods that are annotated with the `@external` decorator. We present the methods following the temporal order of a standard loan interaction.


### `provide_access_to_nft(NFT, payment)`

```
@external
    def provide_access_to_nft(self, nft: abi.Asset, payment: abi.PaymentTransaction):
        return Seq(
            Assert(
                Global.group_size() == Int(2),
                Txn.fee() >= Global.min_txn_fee() * Int(3),
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
```

If B wants to obtain a loan, B must transfer an NFT to the smart contract for the auction. Thus, B must ensure that the smart contract can accept the NFT. `provide_access_to_nft()` is sent by B to the smart contract to trigger the NFT opt-in (the opt-in is a 0-amount transaction that the smart contract sends to itself: `InnerTxnBuilder.Execute({...})`). The smart contract expects to receive an atomic group of exactly two transactions (`Global.group_size() == Int(2)`): a call to `provide_access_to_nft()` and a payment. The payment is needed to satisfy the minimum balance requirements imposed by Algorand (`payment.get().amount() >= self.MIN_BAL`). Moreover, B must pay the fees of three transactions: the two included in the atomic group and the inner transaction generated by the smart contract (`Txn.fee() >= Global.min_txn_fee() * Int(3)`), allowing the smart contract to issue a 0-fee transaction (`TxnField.fee: Int(0)`).



### `set_offer(asset_xfer, auction_base, auction_period, payback_deadline)`
```
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
                asset_xfer.get().asset_receiver() == self.address,
                asset_xfer.get().asset_amount() == Int(1),
                asset_xfer.get().sender() == Txn.sender(),
                Txn.assets[0] == asset_xfer.get().xfer_asset(),      
                asset_manager.value()==Global.zero_address(),  
                asset_clawback.value()==Global.zero_address(), 
                asset_freeze.value()==Global.zero_address(), 
                self.state.get() == Int(0),
                auction_base.get() > Int(0),
                auction_base.get() < self.MAX_N_ALGOS,
                auction_period.get() > Int(0),
                auction_period.get() < self.MAX_AUCTION_PERIOD,
                payback_deadline.get() > Int(0),
                payback_deadline.get() < self.MAX_PAYBACK_DEADLINE,
            ),
            self.state.set(Int(1)),
            self.nft_id.set(asset_xfer.get().xfer_asset()),
            self.auction_base.set(auction_base.get()),
            self.auction_period.set(Global.round()+auction_period.get()),
            self.payback_deadline.set(payback_deadline.get()),
            self.borrower_address.set(Txn.sender())
        ) 
```

Once the smart contract is ready to accept the NFT, B can invoke `set_offer()` to start the auction. B must create an atomic group of two transactions: an asset transfer to the smart contract (`asset_xfer`) and a call to `set_offer()`. B establishes a minimum loan threshold (`auction_base`), the number of blocks of the auction validity period (`auction_period`), and the loan payback deadline (`payback_deadline`), which is the number of blocks from when `accept_bid()` is invoked. The smart contract stores B's address (`borrower_address`) for future ownership transfers. The smart contract performs some checks on the correctness of the transfer transaction, the irrevocability of the received NFT (e.g., clawback address set to the zero address), and the validity of the input parameters. Finally, the smart contract initializes its state variables and starts the auction.


###  `place_bid(payment)`

```
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

```
`place_bid()` is invokable only during the auction validity period. L sends some Algos to the smart contract through an atomic payment transaction. The amount of Algos must be greater than the loan threshold and the current highest bid. The smart contract refunds the previous highest bid and replaces it with the new bid. The smart contract stores L's address (`lender_address`) for future ownership transfers.

### `accept_bid()`



```
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

```


`accept_bid()` is invokable only by B to accept the current highest bid (if any). The smart contract keeps a small percentage of the bid and forwards the remaining part to B (see how `TxnField.amount` is computed). The percentage represents a service fee that CO can collect by invoking the `pay_me()` method. The smart contract updates B's debt, computes the payback deadline, and stores the current block number (to correctly compute the interest in the future). The smart contract still owns the NFT. `cancel_offer()` and `timeout()` can no longer be invoked.
`
### `timeout()`

```
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
```


`timeout()` is invokable only after the auction ends and only if `accept_bid()` was not previously invoked. Anyone can invoke `timeout()` to return the managed assets (the NFT and the bid) to their original owners. B may call `timeout()` if the received offers are too low. L may call `timeout()` to prevent B from indefinitely postponing the offer acceptance. The smart contract uses  `InnerTxnBuilder.Begin()`, `InnerTxnBuilder.Next()`, and `InnerTxnBuilder.Submit()` to create an atomic group of inner transactions. By setting the `TxnField.asset_close_to` field, the smart contract opts out from the asset and reduces its minimum balance requirements. This operation is not strictly necessary and must be carefully performed, as any remaining asset is sent to the close address (even if the `TxnField.asset_amount` field specifies a different amount, as in the code above). 

### `cancel_offer()`

```
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
```

`cancel_offer()` can be invoked only by B. Moreover, only one between `cancel_offer()` and `accept_bid()` can be invoked. The smart contract returns the managed assets (the NFT and the bid) to their original owners. `cancel_offer()` is similar to `timeout()` (only one condition changes:  ` Global.round() > self.auction_period.get()` becomes `Txn.sender() == self.borrower_address.get()` )

### `pay_back(payment)`



```
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
```
 
`pay_back()` can be used to pay back the loan or a portion of it. The smart contract expects to receive an atomic group of exactly two transactions: a call to `pay_back()` and a payment. The payment must pay back at least the accumulated interest (`payment.get().amount() >= interest`). If the payment exceeds B's current debt, the smart contract returns the exceeding Algos to B.

Once `pay_back()` is invoked, the smart contract updates the current debt by summing the accumulated interest. Then, the smart contract subtracts `payment` Algos from B's debt and forwards the `payment` Algos to L. If B's debt goes to 0, the smart contract gives the NFT back to B. `pay_back()` can be invoked after the payback deadline expires but not after `loan_expired()` is invoked.

The smart contract updates the `last_interest_update_block` each time `pay_back()` is invoked. Thus, the interest is computed only on the portion of the debt that is yet to be paid, not on the original loan. The interest rate is `INTEREST_RATE_NUM`/`INTEREST_RATE_DEN`. In the current implementation, `INTEREST_RATE_NUM` and `INTEREST_RATE_DEN` are constants. Thus, the (simple) interest is computed as follows: `interest=debt_left*INTEREST_RATE_NUM*(current_block-last_interest_update_block)/INTEREST_RATE_DEN` (notice that `INTEREST_RATE_NUM=1`)

### `loan_expired()`


```
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
```

`loan_expired()` can be invoked only by L after the payback deadline expires (` Global.round() >= self.payback_deadline.get()`). L receives the NFT from the smart contract. `pay_back()` cannot be invoked anymore.

### `pay_me()`

```
    @external(authorize=Authorize.only(Global.creator_address()))
    def pay_me(self):
        return Seq(
            Assert(
                Balance(self.address) > MinBalance(self.address)
            ),
            self.pay_me_internal()
        )
        
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
```


`pay_me()` can only be invoked by CO (`@external(authorize=Authorize.only(Global.creator_address()))`). `pay_me()` invokes  `pay_me_internal()`, a method annotated with the  `@internal` decorator:  `pay_me_internal()` cannot be invoked directly by the users. `pay_me_internal()` sends the currently collected fees to CO's address and guarantees that the minimum balance requirements are respected (`TxnField.amount: Balance(self.address) - MinBalance(self.address)`). 

# Conclusion
In this solution, we discussed the implementation of a digital pawnshop, where NFT collaterals can be used to obtain loans. The digital pawnshop solves many of the challenges of physical pawnshops. The digital pawnshop differs from liquidity protocols for fungible tokens, as it must address the limited liquidity and high volatility of NFTs.

We conclude by noticing that the ecosystem is very new, and understanding how to handle things may be a little challenging. Nonetheless, the support we received from the developer community is amazing.


