# Group 3 
- [METTERE I NOMI IN ORDINE ALFABETICO]
-

# Algorand NFT Loan System

## Goal of the project
The problem identified is the access to liquidity in terms of cryptocurrency or specific assets that could be addressed with a loan mechanism of owned NFT.

## Smart contract specifications
The smart contract is able to accept an NFT from an account for a period of time, storing info on the global state. During this period other accounts are able to submit an offer (in ALGO or other asset, tbd) for that NFT. After this initial offering period, the owner of the NFT can interact with the contract to get back the NFT (in this case the highest bidded amount return to the bidder) or to accept the loan. In the second case, there is a predefined period of time in which the owner of the NFT must repay the loan to the bidder, otherwise, after the deadline, the loaner can retrieve the NFT interacting with the contract.
So, we have different role:
- The NFT owner
- Other Algorand accounts who bid for the loan
- The Stateful Smart Contract whose state is:
	- NFT owner address
	- NFT id
	- Highest bid's value
	- Highest bidder's address
	- Bidding deadline
	- Pay back deadline
	- Period of the loan (useful in the case that the pay back deadline need to be set once the loan is accepted)

## State of the art  
<Qui andrebbero descritti altri sistemi, ho visto e ne esistono in effetti e fanno cose simili, al netto forse di qualche aggiustamento economico come interessi ecc..>

## Technical challenges 
The possibility to apply economics concept to the loan (i.e. interests).

The possibility to receive specific assets instead of ALGOs.

Smart contract manages group of transactions so it has to be accurate in the evaluation of them.

In order to perform the payback it should use an inner payment transaction to the bidder.

The temporal parameters has to be calculated in terms of blockchain round.

NFT is an Algorand Standard Asset with specific configuration described in the [ARC-0003](https://arc.algorand.foundation/ARCs/arc-0003) .

## Futures and business value
The NFTs loan systems are geining increasing attention because they allow users to access to liquidity simply owning NFTs. A marketplace of this kind of contract on algorand could allow the interoperability between the NFT marketplace and DEFI.
Even more, with algorand state proof this system may interact with other blockchain.