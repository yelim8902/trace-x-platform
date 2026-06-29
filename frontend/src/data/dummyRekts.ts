export const Reckts = [
  {
    "id": 1,
    "projectName": "Euler Finance",
    "title": "Flash Loan Exploit",
    "description": "<p>A sophisticated <strong>flash loan attack</strong> drained funds across multiple lending pools. The attacker leveraged multiple complex transactions to bypass internal validation, resulting in substantial losses.</p>",
    "date": "2023-03-13",
    "fundsLost": "197000000",
    "fundsReturned": "0",
    "chaindIds": [1],
    "category": "Lending",
    "issueType": "Flash Loan Exploit",
    "token": {
      "name": "USDC",
      "addresses": ["0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]
    },
    "logo": "https://cryptologos.cc/logos/usd-coin-usdc-logo.png"
  },
  {
    "id": 2,
    "projectName": "Ronin Network",
    "title": "Bridge Private Key Compromise",
    "description": "<p>The Ronin chain bridge suffered a <strong>private key compromise</strong>, allowing attackers to sign fraudulent withdrawals. A total of 173,600 ETH and 25.5M USDC were drained.</p>",
    "date": "2022-03-29",
    "fundsLost": "625000000",
    "fundsReturned": "0",
    "chaindIds": [1, 56],
    "category": "Bridge",
    "issueType": "Key Compromise",
    "token": {
      "name": "ETH",
      "addresses": ["0x0000000000000000000000000000000000000000"]
    },
    "logo": "https://cryptologos.cc/logos/ethereum-eth-logo.png"
  },
  {
    "id": 3,
    "projectName": "Poly Network",
    "title": "Cross-chain Contract Exploit",
    "description": "<p>An attacker exploited a flaw in <strong>Poly Network's cross-chain contract</strong> to alter the contract owner's privileges, enabling unauthorized asset transfers across multiple chains.</p>",
    "date": "2021-08-12",
    "fundsLost": "611000000",
    "fundsReturned": "609000000",
    "chaindIds": [1, 56, 137],
    "category": "Cross-chain",
    "issueType": "Contract Exploit",
    "token": {
      "name": "Multiple",
      "addresses": [
        "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
        "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"
      ]
    },
    "logo": "https://cryptologos.cc/logos/polygon-matic-logo.png"
  }
]
