#!/bin/bash
# Скрипт очистки для WB Bot
# Запускается автоматически через cron 1-го и 15-го числа

LOG_FILE="/root/wb-bot/cleanup.log"
WORK_DIR="/root/wb-bot"
DB_FILE="$WORK_DIR/wb_orders.db"

echo "=========================================" >> "$LOG_FILE"
echo "АВТООЧИСТКА: $(date '+%d.%m.%Y %H:%M:%S')" >> "$LOG_FILE"
echo "=========================================" >> "$LOG_FILE"

# 1. ЛОГИ SYSTEMD
echo "[1/4] Очистка логов systemd..." >> "$LOG_FILE"
JOURNAL_BEFORE=$(sudo journalctl --disk-usage | grep -oP '\d+\.?\d*[A-Z]')
sudo journalctl --vacuum-time=14d --quiet
JOURNAL_AFTER=$(sudo journalctl --disk-usage | grep -oP '\d+\.?\d*[A-Z]')
echo "   Размер логов: $JOURNAL_BEFORE → $JOURNAL_AFTER" >> "$LOG_FILE"

# 2. БАЗА ДАННЫХ
echo "[2/4] Оптимизация базы данных..." >> "$LOG_FILE"
if [ -f "$DB_FILE" ]; then
    DB_SIZE_BEFORE=$(du -h "$DB_FILE" | awk '{print $1}')
    
    # Создаем резервную копию
    BACKUP_DIR="$WORK_DIR/backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/wb_orders_$(date +%Y%m%d_%H%M%S).db"
    cp "$DB_FILE" "$BACKUP_FILE"
    
    # Оптимизируем
    sqlite3 "$DB_FILE" "VACUUM; ANALYZE;" 2>/dev/null
    
    # Удаляем старые резервные копии (старше 30 дней)
    find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete 2>/dev/null
    
    DB_SIZE_AFTER=$(du -h "$DB_FILE" | awk '{print $1}')
    echo "   База данных: $DB_SIZE_BEFORE → $DB_SIZE_AFTER" >> "$LOG_FILE"
    echo "   Резервная копия: $(basename "$BACKUP_FILE")" >> "$LOG_FILE"
else
    echo "   ⚠️ База данных не найдена" >> "$LOG_FILE"
fi

# 3. КЭШ PYTHON
echo "[3/4] Очистка кэша Python..." >> "$LOG_FILE"
CACHE_COUNT=$(find "$WORK_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null | wc -l)
PYC_COUNT=$(find "$WORK_DIR" -name "*.pyc" -delete 2>/dev/null | wc -l)
echo "   Удалено: $CACHE_COUNT папок __pycache__, $PYC_COUNT файлов .pyc" >> "$LOG_FILE"

# 4. ИНФОРМАЦИЯ О СИСТЕМЕ
echo "[4/4] Статус системы..." >> "$LOG_FILE"
echo "   Диск: $(df -h / | awk 'NR==2 {print $4 " свободно из " $2}')" >> "$LOG_FILE"
echo "   Бот: $(systemctl is-active wbbot)" >> "$LOG_FILE"
echo "   Дата следующей очистки: $(date -d '+14 days' '+%d.%m.%Y')" >> "$LOG_FILE"

echo "" >> "$LOG_FILE"
echo "✅ Очистка завершена успешно!" >> "$LOG_FILE"
echo "=========================================" >> "$LOG_FILE"
