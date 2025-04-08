# Orbiter Finance Bridge Automation

Automated script for bridging ETH between blockchains via Orbiter Finance with multi-threading support and automatic balance refill.

## Features

- 🔄 Multi-threaded processing of multiple wallets simultaneously
- 🔁 Support for multiple runs for maximum efficiency
- 💰 Automatic balance refill when funds are insufficient in the source network
- 📊 Collect mode for concentrating ETH in the target network
- 🔧 Flexible configuration via config file

## Supported Networks

- Base
- Abstract
- Arbitrum
- Linea
- And other networks supported by Orbiter Finance

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/orbiter-bridge-automation.git
cd orbiter-bridge-automation

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Create a `private_keys.txt` file with your wallet private keys (one per line)
2. Edit the `bridge_config.json` file according to your needs:

```json
{
    "src_chain": "Base",
    "dst_chain": "Abstract",
    "private_keys_file": "private_keys.txt",
    "min_amount": 0.0015,
    "max_amount": 0.0020,
    "min_delay": 10,
    "max_delay": 15,
    "min_transactions": 100,
    "max_transactions": 150,
    "auto_refill": true,
    "refill_percent": 96,
    "collect_percent": 95,
    "threads": 3,
    "min_bridge_amount": 0.00055,
    "runs": 5,
    "pause_between_runs": 300
}
```

## Usage

### Standard Mode (Multi-threaded Bridge)

```bash
python main.py
```

### Running with Custom Thread Count

```bash
python main.py --threads 4
```

### Running with Custom Run Count

```bash
python main.py --runs 10
```

### Collect Mode

```bash
python main.py --collect
```

## Example Output

```
2023-03-28 10:15:23 | INFO     | === RUN 1/5 ===
2023-03-28 10:15:23 | INFO     | Loaded wallets: 10
2023-03-28 10:15:23 | INFO     | Settings: Base -> Abstract, 100-150 transactions per wallet, amount 0.001500-0.002000 ETH, delay 10-15 sec.
2023-03-28 10:15:23 | INFO     | Auto-refill: Enabled, refill percent: 96%
2023-03-28 10:15:23 | INFO     | Number of concurrent threads: 3
2023-03-28 10:15:23 | INFO     | Wallet 1/10 (0xA706...a9Ef) | Planned 143 transactions
2023-03-28 10:15:24 | INFO     | Wallet: 0xA706...a9Ef | Balance in Base: 0.023500 ETH
2023-03-28 10:15:25 | INFO     | Wallet: 0xA706...a9Ef | Bridging 0.001785 ETH from Base to Abstract
2023-03-28 10:15:30 | INFO     | Wallet: 0xA706...a9Ef | Bridge successful!
```

## Security

- The script runs locally and does not send data to external servers
- Private keys are stored only in a local file
- It is recommended to use separate wallets only for automation

## Disclaimer

This script is provided "as is" without any warranties. Use at your own risk. The author is not responsible for any losses associated with the use of this script.

