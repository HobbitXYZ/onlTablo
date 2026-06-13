#!/bin/bash
# Usage:
#   ./events_stat.sh          — сегодня
#   ./events_stat.sh all      — за всё время
#   ./events_stat.sh 24/May/2026  — конкретная дата

LOG=/var/log/nginx/access.log
LOG_OLD=/var/log/nginx/access.log.1
FILTER="${1:-$(date +%d/%b/%Y)}"

ALL_LOGS="$LOG"
[ -f "$LOG_OLD" ] && ALL_LOGS="$LOG_OLD $LOG"

if [ "$FILTER" = "all" ]; then
    LABEL="за всё время"
    DATA=$(cat $ALL_LOGS)
else
    LABEL="за $FILTER"
    DATA=$(grep "$FILTER" $ALL_LOGS 2>/dev/null)
fi

echo "Подключения по мероприятиям $LABEL"
echo "====================================="

printf "%-14s %10s %12s\n" "Мероприятие" "Запросов" "Уник. IP"
printf "%-14s %10s %12s\n" "-----------" "--------" "--------"

echo "$DATA" | awk '
{
    ip  = $1
    url = $7
    if (match(url, /^\/([0-9]+)\/?$/, arr)) {
        event = arr[1]
        hits[event]++
        key = event SUBSEP ip
        if (!seen[key]++) uniq[event]++
    }
}
END {
    if (length(hits) == 0) {
        print "Нет данных."
        exit
    }
    for (e in hits)
        printf "%-14s %10d %12d\n", e, hits[e], uniq[e]
}' | sort -k2 -rn
