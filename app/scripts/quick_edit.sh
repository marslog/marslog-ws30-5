#!/bin/bash

# MARSLOG Quick Edit Script
# แก้ไข code โดยตรงบนเครื่อง Linux

echo "🚀 MARSLOG Quick Edit Tool"
echo "========================="

if [ $# -eq 0 ]; then
    echo "Usage examples:"
    echo "./quick_edit.sh replace 'old_text' 'new_text' filename"
    echo "./quick_edit.sh edit filename"
    echo "./quick_edit.sh backup filename"
    echo "./quick_edit.sh restore filename"
    exit 1
fi

ACTION=$1
FILE_PATH="/opt/marslog/app/frontend/auth/login.php"

case $ACTION in
    "replace")
        OLD_TEXT="$2"
        NEW_TEXT="$3"
        if [ -n "$4" ]; then
            FILE_PATH="$4"
        fi
        echo "Replacing '$OLD_TEXT' with '$NEW_TEXT' in $FILE_PATH"
        sed -i "s/$OLD_TEXT/$NEW_TEXT/g" "$FILE_PATH"
        echo "✅ Replacement completed!"
        ;;
    
    "edit")
        if [ -n "$2" ]; then
            FILE_PATH="$2"
        fi
        echo "Opening $FILE_PATH with nano..."
        nano "$FILE_PATH"
        ;;
    
    "backup")
        if [ -n "$2" ]; then
            FILE_PATH="$2"
        fi
        BACKUP_PATH="${FILE_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$FILE_PATH" "$BACKUP_PATH"
        echo "✅ Backup created: $BACKUP_PATH"
        ;;
    
    "restore")
        if [ -n "$2" ]; then
            FILE_PATH="$2"
        fi
        echo "Available backups:"
        ls -la "${FILE_PATH}.backup."* 2>/dev/null || echo "No backups found"
        ;;
    
    "view")
        if [ -n "$2" ]; then
            FILE_PATH="$2"
        fi
        echo "Viewing $FILE_PATH:"
        cat -n "$FILE_PATH" | head -20
        ;;
        
    *)
        echo "Unknown action: $ACTION"
        echo "Available actions: replace, edit, backup, restore, view"
        ;;
esac
