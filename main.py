# -*- coding: utf-8 -*-
import asyncio
import random
import json
import time
import os
import argparse
import logging
from typing import List, Dict, Any

from client import Client
from networks import get_network_by_name
from modules.bridges.orbiter import Orbiter


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class BridgeConfig:
    """Класс для работы с конфигурацией бриджа"""
    def __init__(self, config_path="bridge_config.json"):
        if not os.path.exists(config_path):
            self.create_default_config(config_path)
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.src_chain = config.get("src_chain", "Base")
        self.dst_chain = config.get("dst_chain", "Abstract")
        self.private_keys_file = config.get("private_keys_file", "private_keys.txt")
        self.min_amount = config.get("min_amount", 0.0015)
        self.max_amount = config.get("max_amount", 0.0020)
        self.min_delay = config.get("min_delay", 10)
        self.max_delay = config.get("max_delay", 15)
        
        # Диапазон транзакций вместо точного числа
        self.min_transactions = config.get("min_transactions", 100)
        self.max_transactions = config.get("max_transactions", 150)
        
        # Параметры автоматического пополнения баланса
        self.auto_refill = config.get("auto_refill", True)
        self.refill_percent = config.get("refill_percent", 96)
        
        # Процент для сбора в Abstract (по умолчанию 95%)
        self.collect_percent = config.get("collect_percent", 95)
        
        # Количество одновременно работающих потоков
        self.threads = config.get("threads", 3)
        
        # Минимальная сумма для бриджа (определяется Orbiter для каждой пары сетей)
        self.min_bridge_amount = config.get("min_bridge_amount", 0.00055)
        
        # Количество повторений прогона через все кошельки
        self.runs = config.get("runs", 1)
        
        # Пауза между прогонами (в секундах)
        self.pause_between_runs = config.get("pause_between_runs", 300)
    
    def create_default_config(self, config_path):
        """Создает файл конфигурации по умолчанию, если его нет"""
        default_config = {
            "src_chain": "Base",
            "dst_chain": "Abstract",
            "private_keys_file": "private_keys.txt",
            "min_amount": 0.0015,
            "max_amount": 0.0020,
            "min_delay": 10,
            "max_delay": 15,
            "min_transactions": 100,
            "max_transactions": 150,
            "auto_refill": True,
            "refill_percent": 96,
            "collect_percent": 95,
            "threads": 3,
            "min_bridge_amount": 0.00055,
            "runs": 1,
            "pause_between_runs": 300
        }
        
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        logger.info(f"Создан файл конфигурации по умолчанию: {config_path}")
        logger.info("Пожалуйста, отредактируйте его под ваши нужды и перезапустите скрипт.")


def load_private_keys(file_path):
    """Загружает приватные ключи из файла"""
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            f.write("# Вставьте сюда приватные ключи, по одному на строку\n")
            f.write("# Пример: 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef\n")
        
        logger.info(f"Создан файл для приватных ключей: {file_path}")
        logger.info("Пожалуйста, добавьте в него приватные ключи (по одному на строку) и перезапустите скрипт.")
        return []
    
    with open(file_path, 'r') as f:
        keys = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # Перемешиваем приватные ключи для случайного порядка использования
    random.shuffle(keys)
    
    return keys


async def bridge_eth(src_chain, dst_chain, private_key, amount):
    """Выполняет бридж ETH между цепочками через Orbiter"""
    # Для каждой сети используем правильный токен
    SRC_TOKEN = "ETH"  # Предполагаем, что это нативный токен в обеих сетях
    DST_TOKEN = "ETH"  # Если это не так, требуется модификация этого кода
    
    # Инициализация клиента (без прокси)
    client = Client(
        account_name="bridge_user", 
        network=get_network_by_name(src_chain),
        private_key=private_key,
        proxy=None,  # Явно указываем None для прокси
    )
    
    try:
        async with client:
            # Получаем адрес кошелька для логов
            wallet_address = client.address
            short_address = f"{wallet_address[:6]}...{wallet_address[-4:]}"
            
            logger.info(f"Кошелек: {short_address} | Бридж {amount:.6f} ETH из {src_chain} в {dst_chain}")
            
            # Инициализация Orbiter
            orbiter = Orbiter(client=client)
            
            # Выполнение бриджа и игнорирование возвращаемого значения
            try:
                await orbiter.bridge(
                    src_token_name=SRC_TOKEN,
                    src_chain=get_network_by_name(src_chain),
                    dst_token_name=DST_TOKEN,
                    dst_chain=get_network_by_name(dst_chain),
                    amount_to_bridge_ether=amount,
                )
                logger.info(f"Кошелек: {short_address} | Бридж успешно выполнен!")
                return True
            except Exception as e:
                logger.error(f"Кошелек: {short_address} | Ошибка в методе bridge: {str(e)}")
                return False
    except Exception as e:
        logger.error(f"Ошибка при выполнении бриджа: {str(e)}")
        return False


async def get_eth_balance(network_name, private_key):
    """Получает баланс ETH в указанной сети"""
    client = Client(
        account_name="balance_check", 
        network=get_network_by_name(network_name),
        private_key=private_key,
        proxy=None,  # Явно указываем None для прокси
    )
    
    try:
        async with client:
            short_address = f"{client.address[:6]}...{client.address[-4:]}"
            
            # Проверка на специальные случаи, если ETH является токеном, а не нативной валютой
            # В Base и Abstract предполагаем, что ETH - нативная валюта
            balance_wei = await client.w3.eth.get_balance(client.address)
            balance_eth = float(client.from_wei(balance_wei))
            
            logger.info(f"Кошелек: {short_address} | Баланс в {network_name}: {balance_eth:.6f} ETH")
            return balance_eth
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {str(e)}")
        return 0.0


async def refill_from_abstract_to_base(private_key, refill_percent, min_bridge_amount):
    """Выполняет пополнение баланса в Base, переводя указанный процент ETH из Abstract"""
    try:
        # Получаем баланс в Abstract
        abstract_balance = await get_eth_balance("Abstract", private_key)
        
        if abstract_balance <= 0.001:  # Порог с запасом на газ
            logger.warning("Недостаточно средств в Abstract для пополнения баланса в Base")
            return False
        
        # Рассчитываем сумму для пополнения (refill_percent% от баланса)
        # Преобразуем refill_percent в float для безопасности
        refill_amount = abstract_balance * (float(refill_percent) / 100.0)
        
        # Оставляем немного ETH для газа
        if refill_amount > (abstract_balance - 0.001):
            refill_amount = abstract_balance - 0.001
        
        # Проверяем минимальный порог для бриджа
        if refill_amount < min_bridge_amount:
            logger.warning(f"Сумма для пополнения слишком мала: {refill_amount:.6f} ETH (минимум {min_bridge_amount} ETH)")
            return False
        
        logger.info(f"Пополнение баланса в Base: отправка {refill_amount:.6f} ETH ({refill_percent}% от баланса в Abstract)")
        
        # Выполняем бридж из Abstract в Base
        success = await bridge_eth("Abstract", "Base", private_key, refill_amount)
        
        if success:
            # Даем время на обработку бриджа
            logger.info("Ожидаем 120 секунд для обработки бриджа...")
            await asyncio.sleep(120)
            # Проверяем, появились ли средства
            base_balance = await get_eth_balance("Base", private_key)
            if base_balance > min_bridge_amount:
                logger.info(f"Средства успешно поступили в Base. Новый баланс: {base_balance:.6f} ETH")
                return True
            else:
                logger.warning("Средства еще не поступили в Base. Увеличиваем время ожидания...")
                await asyncio.sleep(60)  # Ждем еще минуту
                base_balance = await get_eth_balance("Base", private_key)
                if base_balance > min_bridge_amount:
                    logger.info(f"Средства поступили после дополнительного ожидания. Баланс: {base_balance:.6f} ETH")
                    return True
                else:
                    logger.warning("Средства так и не поступили в Base после ожидания.")
                    return False
        
        return success
    except Exception as e:
        logger.error(f"Ошибка при пополнении баланса: {str(e)}")
        import traceback
        logger.debug(f"Подробный стек вызовов: {traceback.format_exc()}")
        return False


async def collect_from_base_to_abstract(private_key, collect_percent, min_bridge_amount):
    """Собирает ETH из Base в Abstract, переводя указанный процент баланса"""
    try:
        # Получаем баланс в Base
        base_balance = await get_eth_balance("Base", private_key)
        
        if base_balance <= 0.001:  # Минимальный порог для бриджа с запасом
            logger.warning("Недостаточно средств в Base для сбора в Abstract (меньше 0.001 ETH)")
            return False
        
        # Рассчитываем сумму для сбора (collect_percent% от баланса)
        collect_amount = base_balance * (float(collect_percent) / 100.0)
        
        # Проверяем минимальные требования для бриджа
        if collect_amount < min_bridge_amount:
            logger.warning(f"Слишком маленькая сумма для бриджа: {collect_amount:.6f} ETH (минимум {min_bridge_amount} ETH)")
            return False
        
        logger.info(f"Сбор ETH в Abstract: отправка {collect_amount:.6f} ETH ({collect_percent}% от баланса в Base)")
        
        # Выполняем бридж из Base в Abstract
        success = await bridge_eth("Base", "Abstract", private_key, collect_amount)
        return success
    except Exception as e:
        logger.error(f"Ошибка при сборе баланса: {str(e)}")
        import traceback
        logger.debug(f"Подробный стек вызовов: {traceback.format_exc()}")
        return False


async def process_wallet(private_key, config, wallet_index, total_wallets):
    """Обрабатывает один кошелек, выполняя несколько транзакций"""
    client = Client(
        account_name=f"wallet_{wallet_index}", 
        network=get_network_by_name(config.src_chain),
        private_key=private_key,
        proxy=None,
    )
    
    try:
        async with client:
            wallet_address = client.address
            short_address = f"{wallet_address[:6]}...{wallet_address[-4:]}"
            
            # Определяем случайное количество транзакций в указанном диапазоне
            transactions_count = random.randint(config.min_transactions, config.max_transactions)
            logger.info(f"Кошелек {wallet_index}/{total_wallets} ({short_address}) | Запланировано {transactions_count} транзакций")
            
            completed_transactions = 0
            refill_attempts = 0  # Счетчик попыток пополнения
            max_refill_attempts = 3  # Максимальное количество попыток пополнения
            
            while completed_transactions < transactions_count:
                try:
                    # Генерируем случайную сумму для транзакции
                    amount = random.uniform(config.min_amount, config.max_amount)
                    
                    # Проверяем баланс в исходной цепи перед транзакцией
                    balance = await get_eth_balance(config.src_chain, private_key)
                    
                    # Если баланса недостаточно и включено автоматическое пополнение
                    if balance < amount and config.auto_refill and refill_attempts < max_refill_attempts:
                        logger.info(f"Кошелек {short_address} | Недостаточно средств в {config.src_chain}. Пополняем баланс из Abstract...")
                        refill_attempts += 1
                        
                        # Пробуем пополнить баланс из Abstract в Base
                        if await refill_from_abstract_to_base(private_key, config.refill_percent, config.min_bridge_amount):
                            logger.info(f"Кошелек {short_address} | Баланс успешно пополнен. Продолжаем транзакции...")
                            continue
                        else:
                            logger.warning(f"Кошелек {short_address} | Не удалось пополнить баланс. Попытка {refill_attempts} из {max_refill_attempts}.")
                            if refill_attempts >= max_refill_attempts:
                                logger.warning(f"Кошелек {short_address} | Достигнуто максимальное количество попыток пополнения. Прекращаем операции.")
                                break
                            # Даем время перед следующей попыткой
                            await asyncio.sleep(30)
                            continue
                    
                    # Если баланса все равно недостаточно или исчерпаны попытки пополнения
                    if balance < amount:
                        if config.auto_refill and refill_attempts < max_refill_attempts:
                            # Если еще есть попытки, пробуем еще раз
                            logger.info(f"Кошелек {short_address} | Пробуем еще раз пополнить баланс...")
                            continue
                        else:
                            logger.warning(f"Кошелек {short_address} | Недостаточно средств в {config.src_chain} для транзакции. Прекращаем операции.")
                            break
                    
                    # Выполняем бридж
                    success = await bridge_eth(config.src_chain, config.dst_chain, private_key, amount)
                    
                    if success:
                        completed_transactions += 1
                        logger.info(f"Кошелек {short_address} | Выполнено {completed_transactions} из {transactions_count} транзакций")
                        
                        # Если нужно выполнить еще транзакции, делаем паузу
                        if completed_transactions < transactions_count:
                            delay = random.randint(config.min_delay, config.max_delay)
                            logger.info(f"Кошелек {short_address} | Ожидание {delay} секунд перед следующей транзакцией...")
                            await asyncio.sleep(delay)
                    else:
                        logger.warning(f"Кошелек {short_address} | Транзакция не удалась, пробуем еще раз...")
                        # Короткая пауза перед повторной попыткой
                        await asyncio.sleep(10)
                except Exception as e:
                    logger.error(f"Кошелек {short_address} | Ошибка при обработке: {str(e)}")
                    await asyncio.sleep(10)  # Пауза перед продолжением после ошибки
                    continue
            
            logger.info(f"Кошелек {short_address} | Обработка завершена, выполнено {completed_transactions} транзакций")
            return completed_transactions > 0
    except Exception as e:
        logger.error(f"Критическая ошибка при обработке кошелька {wallet_index}: {str(e)}")
        return False


async def run_wallet_group(private_keys, config, start_index, end_index, total_wallets):
    """Обрабатывает группу кошельков последовательно в одном потоке"""
    for i in range(start_index, min(end_index, len(private_keys))):
        private_key = private_keys[i]
        wallet_index = i + 1
        
        success = await process_wallet(private_key, config, wallet_index, total_wallets)
        
        # Пауза между кошельками только если не последни� кошелек в группе
        if i < end_index - 1 and i < len(private_keys) - 1:
            delay = random.randint(config.min_delay, config.max_delay)
            logger.info(f"Ожидание {delay} секунд перед обработкой следующего кошелька...")
            await asyncio.sleep(delay)


async def collect_balances(config, private_keys):
    """Собирает балансы всех кошельков из Base в Abstract"""
    logger.info("\n=== РЕЖИМ СБОРА СРЕДСТВ ===")
    
    if not private_keys:
        logger.warning("Не найдено приватных ключей. Пожалуйста, добавьте их в файл и перезапустите скрипт.")
        return
    
    logger.info(f"Загружено кошельков: {len(private_keys)}")
    logger.info(f"Процент сбора из Base в Abstract: {config.collect_percent}%")
    
    # Создаем список задач для обработки в несколько потоков
    tasks = []
    threads = min(config.threads, len(private_keys))
    wallets_per_thread = len(private_keys) // threads + (1 if len(private_keys) % threads else 0)
    
    for thread_idx in range(threads):
        start_idx = thread_idx * wallets_per_thread
        end_idx = min(start_idx + wallets_per_thread, len(private_keys))
        
        if start_idx >= len(private_keys):
            break
            
        tasks.append(collect_group_balances(
            private_keys[start_idx:end_idx], 
            config.collect_percent, 
            config.min_bridge_amount,
            start_idx, 
            end_idx,
            config.min_delay,
            config.max_delay
        ))
    
    # Запускаем все задачи параллельно
    results = await asyncio.gather(*tasks)
    
    # Суммируем результаты
    successful_transfers = sum(results)
    
    logger.info(f"\nСбор средств завершен. Успешных переводов: {successful_transfers} из {len(private_keys)}")


async def collect_group_balances(private_keys, collect_percent, min_bridge_amount, start_idx, end_idx, min_delay, max_delay):
    """Собирает балансы группы кошельков из Base в Abstract"""
    successful = 0
    
    for i, private_key in enumerate(private_keys):
        wallet_idx = start_idx + i + 1
        
        # Инициализируем клиент для получения адреса
        client = Client(
            account_name=f"collect_{wallet_idx}", 
            network=get_network_by_name("Base"),
            private_key=private_key,
            proxy=None,
        )
        
        try:
            async with client:
                short_address = f"{client.address[:6]}...{client.address[-4:]}"
                logger.info(f"Сбор средств | Кошелек {wallet_idx} ({short_address})")
                
                # Собираем ETH из Base в Abstract
                success = await collect_from_base_to_abstract(private_key, collect_percent, min_bridge_amount)
                
                if success:
                    successful += 1
                
                # Делаем паузу между кошельками если не последний
                if i < len(private_keys) - 1:
                    delay = random.randint(min_delay, max_delay)
                    logger.info(f"Ожидание {delay} секунд перед следующим кошельком...")
                    await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Ошибка при сборе средств кошелька {wallet_idx}: {str(e)}")
    
    return successful


async def run_processing(config, private_keys, run_number, total_runs):
    """Запускает один полный прогон обработки всех кошельков"""
    logger.info(f"\n=== ПРОГОН {run_number}/{total_runs} ===")
    
    # Стандартный режим работы с транзакциями
    logger.info(f"Загружено кошельков: {len(private_keys)}")
    logger.info(f"Настройки: {config.src_chain} -> {config.dst_chain}, "
          f"{config.min_transactions}-{config.max_transactions} транзакций на кошелек, "
          f"сумма {config.min_amount:.6f}-{config.max_amount:.6f} ETH, "
          f"задержка {config.min_delay}-{config.max_delay} сек.")
    logger.info(f"Автоматическое пополнение: {'Включено' if config.auto_refill else 'Выключено'}, "
          f"процент пополнения: {config.refill_percent}%")
    logger.info(f"Количество одновременных потоков: {config.threads}")
    
    # Определяем количество кошельков на поток
    threads = min(config.threads, len(private_keys))
    wallets_per_thread = len(private_keys) // threads + (1 if len(private_keys) % threads else 0)
    
    # Создаем список задач для обработки в несколько потоков
    tasks = []
    for thread_idx in range(threads):
        start_idx = thread_idx * wallets_per_thread
        end_idx = min(start_idx + wallets_per_thread, len(private_keys))
        
        if start_idx >= len(private_keys):
            break
            
        tasks.append(run_wallet_group(
            private_keys, 
            config, 
            start_idx, 
            end_idx,
            len(private_keys)
        ))
    
    # Запускаем все задачи параллельно
    await asyncio.gather(*tasks)
    
    logger.info(f"\nПрогон {run_number}/{total_runs} завершен!")


async def main():
    """Основная функция для запуска скрипта"""
    try:
        # Парсинг аргументов командной строки
        parser = argparse.ArgumentParser(description='Скрипт для бриджа ETH между сетями')
        parser.add_argument('--collect', action='store_true', help='Режим сбора средств из Base в Abstract')
        parser.add_argument('--threads', type=int, help='Количество одновременных потоков')
        parser.add_argument('--runs', type=int, help='Количество повторений прогона')
        args = parser.parse_args()
        
        # Загружаем конфигурацию
        config = BridgeConfig()
        
        # Переопределяем параметры, если указаны в аргументах
        if args.threads:
            config.threads = args.threads
        if args.runs:
            config.runs = args.runs
            
        # Загружаем приватные ключи (в случайном порядке)
        private_keys = load_private_keys(config.private_keys_file)
        
        if not private_keys:
            logger.warning("Не найдено приватных ключей. Пожалуйста, добавьте их в файл и перезапустите скрипт.")
            return
        
        # Если включен режим сбора средств
        if args.collect:
            await collect_balances(config, private_keys)
            return
        
        # Запускаем несколько прогонов
        for run in range(1, config.runs + 1):
            # Выполняем один полный прогон
            await run_processing(config, private_keys, run, config.runs)
            
            # Если это не последний прогон, делаем паузу
            if run < config.runs:
                logger.info(f"Пауза {config.pause_between_runs} секунд перед следующим прогоном...")
                await asyncio.sleep(config.pause_between_runs)
        
        logger.info("\nВсе операции выполнены!")
    except Exception as e:
        logger.error(f"Критическая ошибка в main: {str(e)}")
        import traceback
        logger.error(f"Подробный стек вызовов: {traceback.format_exc()}")


if __name__ == "__main__":
    # Запускаем асинхронную функцию main
    asyncio.run(main())
