import asyncio
import json
import time
import random
from eth_account import Account
from eth_account.messages import encode_defunct
import aiohttp
from typing import Dict, List, Optional
import sys


# Konfigurasi game
GAMES = {
    "snake": {
        "name": "Snake",
        "type": "snake",
        "referrer": "https://play.irys.xyz/snake",
        "emoji": "🐍",
        "reward_tiers": [
            {"min_score": 1000, "reward": 0.01},
            {"min_score": 750, "reward": 0.008},
            {"min_score": 0, "reward": 0.005}
        ],
        "auto_min": 1000,
        "auto_max": 1500,
        "absolute_max": 2000
    },
    "asteroids": {
        "name": "Asteroids",
        "type": "asteroids",
        "referrer": "https://play.irys.xyz/asteroids",
        "emoji": "🚀",
        "reward_tiers": [
            {"min_score": 500000, "reward": 0.01},
            {"min_score": 300000, "reward": 0.008},
            {"min_score": 0, "reward": 0.005}
        ],
        "auto_min": 500000,
        "auto_max": 700000,
        "absolute_max": 1000000
    },
    "missilecommand": {
        "name": "Missile Command",
        "type": "missile-command",
        "referrer": "https://play.irys.xyz/missile",
        "emoji": "💥",
        "reward_tiers": [
            {"min_score": 1600000, "reward": 0.01},
            {"min_score": 800000, "reward": 0.008},
            {"min_score": 0, "reward": 0.005}
        ],
        "auto_min": 1600000,
        "auto_max": 2000000,
        "absolute_max": 3000000
    },
    "hexshot": {
        "name": "Hexshot",
        "type": "hex-shooter",
        "referrer": "https://play.irys.xyz/hexshot",
        "emoji": "🎯",
        "reward_tiers": [
            {"min_score": 65000, "reward": 0.01},
            {"min_score": 55000, "reward": 0.008},
            {"min_score": 0, "reward": 0.005}
        ],
        "auto_min": 65000,
        "auto_max": 80000,
        "absolute_max": 100000
    }
}


# Konfigurasi retry
RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 2,
    "factor": 1.5,
    "max_delay": 10,
    "timeout": 60
}


class Colors:
    """ANSI color codes untuk terminal"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    WHITE = "\033[97m"


def clear_screen():
    """Clear terminal screen"""
    print("\033[2J\033[H", end="")


def print_header():
    """Display aesthetic header"""
    clear_screen()
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔═══════════════════════════════════════╗")
    print("║      IRYS PLAY GAME - BY GIEMDFK      ║")
    print("╚═══════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")


def print_separator(char="─", length=45):
    """Print separator line"""
    print(f"{Colors.CYAN}{char * length}{Colors.RESET}")


def print_info(message: str, emoji: str = "ℹ️"):
    """Print info message"""
    print(f"{Colors.CYAN}{emoji} {message}{Colors.RESET}")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def read_private_keys() -> List[str]:
    """Membaca private key dari file"""
    try:
        with open("privkey.txt", "r") as f:
            keys = [line.strip() for line in f if line.strip()]
        return keys
    except FileNotFoundError:
        print_error("File privkey.txt tidak ditemukan!")
        return []


def format_score(score: int) -> str:
    """Format score untuk display"""
    if score >= 1000000:
        return f"{score / 1000000:.1f}M"
    elif score >= 1000:
        return f"{score / 1000:.1f}K"
    return str(score)


def get_expected_reward(score: int, game: Dict) -> float:
    """Hitung expected reward berdasarkan score"""
    for tier in game["reward_tiers"]:
        if score >= tier["min_score"]:
            return tier["reward"]
    return 0.005


def generate_score(min_score: int, max_score: int) -> int:
    """Generate random score dalam range"""
    return random.randint(min_score, max_score)


def generate_session_id(timestamp: int) -> str:
    """Generate session ID yang sesuai format API"""
    random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    return f"game_{timestamp}_{random_suffix}"


async def create_signature(private_key: str, message: str) -> str:
    """Membuat signature dari message"""
    try:
        # Tambahkan 0x prefix jika belum ada
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
            
        account = Account.from_key(private_key)
        encoded_msg = encode_defunct(text=message)
        signed = account.sign_message(encoded_msg)
        
        # Pastikan signature format 0x...
        sig_hex = signed.signature.hex()
        if not sig_hex.startswith('0x'):
            sig_hex = '0x' + sig_hex
            
        return sig_hex
    except Exception as e:
        raise Exception(f"Signature error: {str(e)}")


async def fetch_with_retry(session: aiohttp.ClientSession, url: str, method: str, **kwargs) -> Optional[Dict]:
    """Fetch dengan retry mechanism"""
    last_error = None

    for attempt in range(RETRY_CONFIG["max_retries"]):
        try:
            async with session.request(method, url, timeout=aiohttp.ClientTimeout(total=RETRY_CONFIG["timeout"]), **kwargs) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        return json.loads(response_text)
                    except:
                        return None
                elif response.status >= 500 or response.status == 429:
                    raise Exception(f"Server error: {response.status}")
                else:
                    # Print error response untuk debugging
                    if attempt == 0:  # Only print on first attempt
                        print(f"\n{Colors.RED}Response {response.status}: {response_text[:300]}{Colors.RESET}")
                    return None
        except asyncio.TimeoutError:
            last_error = "Timeout"
            if attempt < RETRY_CONFIG["max_retries"] - 1:
                delay = min(RETRY_CONFIG["initial_delay"] * (RETRY_CONFIG["factor"] ** attempt), RETRY_CONFIG["max_delay"])
                await asyncio.sleep(delay)
        except Exception as e:
            last_error = e
            if attempt < RETRY_CONFIG["max_retries"] - 1:
                delay = min(RETRY_CONFIG["initial_delay"] * (RETRY_CONFIG["factor"] ** attempt), RETRY_CONFIG["max_delay"])
                await asyncio.sleep(delay)

    return None


async def join_game(session: aiohttp.ClientSession, private_key: str, game: Dict) -> Optional[Dict]:
    """Join game"""
    try:
        # Tambahkan 0x prefix jika belum ada
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
            
        account = Account.from_key(private_key)
        player_address = account.address
        game_cost = 0.001
        timestamp = int(time.time() * 1000)
        session_id = generate_session_id(timestamp)

        # Format message PERSIS seperti di OKX Wallet screenshot
        message = (
            f"I authorize payment of {game_cost} IRYS to play a game on Irys Arcade.\n"
            f"\n"
            f"Player: {player_address}\n"
            f"Amount: {game_cost} IRYS\n"
            f"Timestamp: {timestamp}\n"
            f"\n"
            f"This signature confirms I own this wallet and authorize the payment."
        )
        
        signature = await create_signature(private_key, message)

        # Join request
        payload = {
            "playerAddress": player_address,
            "gameCost": game_cost,
            "signature": signature,
            "message": message,
            "timestamp": timestamp,
            "sessionId": session_id,
            "gameType": game["type"]
        }

        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "referer": game["referrer"]
        }

        result = await fetch_with_retry(session, "https://play.irys.xyz/api/game/start", "POST", json=payload, headers=headers)

        if result and result.get("success"):
            return {
                "success": True,
                "session_id": result["data"]["sessionId"],
                "player_address": player_address,
                "game": game
            }

        return None
    except Exception as e:
        print(f"\n{Colors.RED}Join error: {str(e)}{Colors.RESET}")
        return None


async def complete_game(session: aiohttp.ClientSession, private_key: str, game_data: Dict, score: int) -> Optional[Dict]:
    """Complete game"""
    try:
        # Tambahkan 0x prefix jika belum ada
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
            
        account = Account.from_key(private_key)
        player_address = game_data["player_address"]
        session_id = game_data["session_id"]
        game = game_data["game"]
        timestamp = int(time.time() * 1000)
        game_type = game["type"]

        # Format message PERSIS seperti format join
        message = (
            f"I completed a {game_type} game on Irys Arcade.\n"
            f"\n"
            f"Player: {player_address}\n"
            f"Game: {game_type}\n"
            f"Score: {score}\n"
            f"Session: {session_id}\n"
            f"Timestamp: {timestamp}\n"
            f"\n"
            f"This signature confirms I own this wallet and completed this game."
        )
        
        signature = await create_signature(private_key, message)

        # Complete request
        payload = {
            "playerAddress": player_address,
            "gameType": game["type"],
            "score": score,
            "signature": signature,
            "message": message,
            "timestamp": timestamp,
            "sessionId": session_id
        }

        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "referer": game["referrer"]
        }

        result = await fetch_with_retry(session, "https://play.irys.xyz/api/game/complete", "POST", json=payload, headers=headers)

        if result and result.get("success"):
            reward = result["data"]["rewardAmount"]
            profit = reward - 0.001
            return {
                "success": True,
                "score": result["data"]["score"],
                "reward": reward,
                "profit": profit,
                "game_name": game["name"]
            }

        return None
    except Exception as e:
        print(f"\n{Colors.RED}Complete error: {str(e)}{Colors.RESET}")
        return None


async def play_single_game(session: aiohttp.ClientSession, private_key: str, game: Dict, wallet_num: int, total_wallets: int) -> Optional[Dict]:
    """Play single game"""
    # Tambahkan 0x prefix jika belum ada
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
        
    account = Account.from_key(private_key)
    address = account.address

    print(f"\n{Colors.BOLD}{Colors.WHITE}[{wallet_num}/{total_wallets}] {game['emoji']} {game['name']} {Colors.RESET}")
    print(f"{Colors.CYAN}    Address: {address[:8]}...{address[-6:]}{Colors.RESET}")

    # Join game
    print(f"{Colors.YELLOW}    ⏳ Joining game...{Colors.RESET}", end="", flush=True)
    join_result = await join_game(session, private_key, game)

    if not join_result:
        print(f"\r{Colors.RED}    ✗ Join failed{Colors.RESET}           ")
        return None

    print(f"\r{Colors.GREEN}    ✓ Joined successfully{Colors.RESET}      ")

    # Play time
    play_time = random.randint(30, 60)
    print(f"{Colors.CYAN}    ⏱  Playing for {play_time}s...{Colors.RESET}", end="", flush=True)
    await asyncio.sleep(play_time)
    print(f"\r{Colors.GREEN}    ✓ Play completed{Colors.RESET}           ")

    # Generate score
    score = generate_score(game["auto_min"], game["auto_max"])

    # Complete game
    print(f"{Colors.YELLOW}    ⏳ Submitting score {format_score(score)}...{Colors.RESET}", end="", flush=True)
    complete_result = await complete_game(session, private_key, join_result, score)

    if not complete_result:
        print(f"\r{Colors.RED}    ✗ Complete failed{Colors.RESET}          ")
        return None

    print(f"\r{Colors.GREEN}    ✓ Score: {format_score(complete_result['score'])} | Reward: {complete_result['reward']} IRYS | Profit: +{complete_result['profit']:.4f}{Colors.RESET}")

    return complete_result


async def run_all_games(session: aiohttp.ClientSession, private_key: str, wallet_num: int, total_wallets: int) -> List[Dict]:
    """Run semua game untuk satu wallet"""
    results = []
    game_order = ["snake", "asteroids", "missilecommand", "hexshot"]

    for idx, game_key in enumerate(game_order):
        game = GAMES[game_key]
        result = await play_single_game(session, private_key, game, wallet_num, total_wallets)

        if result:
            results.append(result)

        # Delay antar game
        if idx < len(game_order) - 1:
            delay = random.randint(3, 8)
            print(f"{Colors.CYAN}    ⏱  Next game in {delay}s...{Colors.RESET}")
            await asyncio.sleep(delay)

    return results


def display_menu():
    """Display game menu"""
    print(f"{Colors.BOLD}{Colors.CYAN}╔═══════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║           SELECT GAME MODE            ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚═══════════════════════════════════════╝{Colors.RESET}\n")

    print(f"{Colors.WHITE}  1. {Colors.GREEN}🐍 Snake         {Colors.CYAN}[{GAMES['snake']['auto_min']}-{GAMES['snake']['auto_max']}]{Colors.RESET}")
    print(f"{Colors.WHITE}  2. {Colors.GREEN}🚀 Asteroids     {Colors.CYAN}[{GAMES['asteroids']['auto_min']}-{GAMES['asteroids']['auto_max']}]{Colors.RESET}")
    print(f"{Colors.WHITE}  3. {Colors.GREEN}💥 Missile       {Colors.CYAN}[{GAMES['missilecommand']['auto_min']}-{GAMES['missilecommand']['auto_max']}]{Colors.RESET}")
    print(f"{Colors.WHITE}  4. {Colors.GREEN}🎯 Hexshot       {Colors.CYAN}[{GAMES['hexshot']['auto_min']}-{GAMES['hexshot']['auto_max']}]{Colors.RESET}")
    print(f"{Colors.WHITE}  5. {Colors.YELLOW}🎮 Run All Games (AUTO){Colors.RESET}\n")
    print_separator()


def get_game_choice() -> Dict:
    """Get game choice from user"""
    while True:
        try:
            choice = input(f"{Colors.BOLD}Select mode (1-5): {Colors.RESET}").strip()

            if choice == "1":
                return {"mode": "single", "game": GAMES["snake"]}
            elif choice == "2":
                return {"mode": "single", "game": GAMES["asteroids"]}
            elif choice == "3":
                return {"mode": "single", "game": GAMES["missilecommand"]}
            elif choice == "4":
                return {"mode": "single", "game": GAMES["hexshot"]}
            elif choice == "5":
                return {"mode": "all"}
            else:
                print_error("Invalid choice, please select 1-5")
        except KeyboardInterrupt:
            print(f"\n{Colors.RED}Cancelled by user{Colors.RESET}")
            sys.exit(0)


def display_summary(stats: Dict, mode: str, total_games: int):
    """Display final summary"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}╔═══════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║              SUMMARY                  ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚═══════════════════════════════════════╝{Colors.RESET}\n")

    success_rate = (stats["success"] / total_games * 100) if total_games > 0 else 0
    print(f"{Colors.WHITE}  Success Rate : {Colors.GREEN}{stats['success']}/{total_games} ({success_rate:.1f}%){Colors.RESET}")
    print(f"{Colors.WHITE}  Total Reward : {Colors.YELLOW}{stats['total_reward']:.4f} IRYS{Colors.RESET}")
    print(f"{Colors.WHITE}  Total Cost   : {Colors.RED}{(total_games * 0.001):.4f} IRYS{Colors.RESET}")
    print(f"{Colors.WHITE}  Net Profit   : {Colors.GREEN}{stats['total_profit']:.4f} IRYS{Colors.RESET}")

    if stats["total_profit"] > 0:
        roi = (stats["total_profit"] / (total_games * 0.001)) * 100
        print(f"{Colors.WHITE}  ROI          : {Colors.CYAN}{roi:.1f}%{Colors.RESET}")

    if mode == "all":
        print(f"\n{Colors.CYAN}  Game Stats:{Colors.RESET}")
        for game_name, count in stats["games"].items():
            if count > 0:
                print(f"{Colors.WHITE}    • {game_name}: {Colors.GREEN}{count}{Colors.RESET}")

    print(f"\n{Colors.BOLD}{Colors.GREEN}✨ Bot finished!{Colors.RESET}\n")


async def main():
    """Main function"""
    print_header()

    # Read private keys
    private_keys = read_private_keys()
    if not private_keys:
        print_error("No private keys found in privkey.txt")
        return

    print_success(f"Loaded {len(private_keys)} wallet(s)")
    print()

    # Display menu
    display_menu()

    # Get choice
    choice = get_game_choice()

    print(f"\n{Colors.BOLD}{Colors.GREEN}🚀 Starting bot...{Colors.RESET}")
    print_separator()

    # Initialize stats
    stats = {
        "success": 0,
        "failed": 0,
        "total_reward": 0.0,
        "total_profit": 0.0,
        "games": {"Snake": 0, "Asteroids": 0, "Missile Command": 0, "Hexshot": 0}
    }

    # Create session
    async with aiohttp.ClientSession() as session:
        for idx, private_key in enumerate(private_keys, 1):
            if choice["mode"] == "all":
                # Run all games
                results = await run_all_games(session, private_key, idx, len(private_keys))

                for result in results:
                    stats["success"] += 1
                    stats["total_reward"] += result["reward"]
                    stats["total_profit"] += result["profit"]
                    stats["games"][result["game_name"]] += 1
                    
                if len(results) < 4:
                    stats["failed"] += (4 - len(results))

            elif choice["mode"] == "single":
                # Run single game
                result = await play_single_game(session, private_key, choice["game"], idx, len(private_keys))

                if result:
                    stats["success"] += 1
                    stats["total_reward"] += result["reward"]
                    stats["total_profit"] += result["profit"]
                    stats["games"][result["game_name"]] += 1
                else:
                    stats["failed"] += 1

            # Delay between wallets
            if idx < len(private_keys):
                delay = random.randint(30, 50)
                print(f"\n{Colors.CYAN}💤 Waiting {delay}s before next wallet...{Colors.RESET}")
                await asyncio.sleep(delay)

    # Calculate total games
    if choice["mode"] == "all":
        total_games = len(private_keys) * 4
    else:
        total_games = len(private_keys)

    # Display summary
    display_summary(stats, choice["mode"], total_games)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}✗ Bot stopped by user{Colors.RESET}")
        sys.exit(0)
