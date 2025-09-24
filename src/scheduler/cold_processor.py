#!/usr/bin/env python3
"""
Независимый процессор холодных токенов
Обходит проблемы с APScheduler
"""

import asyncio
import logging
from datetime import datetime, timezone

log = logging.getLogger("cold_processor")

class ColdTokenProcessor:
    def __init__(self, interval_seconds: int = 30):
        self.interval = interval_seconds
        self.running = False
        self.task = None
    
    async def start(self):
        """Запустить обработку холодных токенов"""
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self._process_loop())
        log.info("cold_processor_started", extra={"extra": {"interval": self.interval}})
    
    async def stop(self):
        """Остановить обработку"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        log.info("cold_processor_stopped")
    
    async def _process_loop(self):
        """Основной цикл обработки"""
        # Ждем 15 секунд после старта, чтобы система инициализировалась
        await asyncio.sleep(15)
        
        while self.running:
            try:
                await self._process_cold_tokens()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in cold processor loop: {e}")
                await asyncio.sleep(5)  # Короткая пауза при ошибке
    
    async def _process_cold_tokens(self):
        """Обработать холодные токены"""
        try:
            from src.scheduler.service import _process_group
            await _process_group("cold")
        except Exception as e:
            log.error(f"Failed to process cold tokens: {e}")

# Глобальный экземпляр процессора
_cold_processor = None

def get_cold_processor() -> ColdTokenProcessor:
    """Получить глобальный экземпляр процессора"""
    global _cold_processor
    if _cold_processor is None:
        _cold_processor = ColdTokenProcessor()
    return _cold_processor

async def start_cold_processor(interval_seconds: int = 30):
    """Запустить процессор холодных токенов"""
    processor = get_cold_processor()
    processor.interval = interval_seconds
    await processor.start()

async def stop_cold_processor():
    """Остановить процессор холодных токенов"""
    processor = get_cold_processor()
    await processor.stop()