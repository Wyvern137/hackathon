"""
Расширенные обработчики командной работы с ролями и workflow
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.database.models import Team, TeamMember, SharedContent, ContentComment, ContentHistory, TeamRole
from bot.database.database import get_db
from bot.utils.helpers import get_or_create_user
from bot.states.conversation import END
from datetime import datetime

logger = logging.getLogger(__name__)


async def show_team_advanced_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расширенное меню командной работы"""
    user_id = update.effective_user.id
    
    with get_db() as db:
        # Получаем команды пользователя
        user_teams = db.query(TeamMember).filter(
            TeamMember.user_id == user_id
        ).all()
        
        owned_teams = db.query(Team).filter(
            Team.owner_id == user_id
        ).all()
    
    text = "👥 **Командная работа**\n\n"
    
    if user_teams or owned_teams:
        text += "**Твои команды:**\n"
        for member in user_teams[:5]:
            team = member.team
            role_emoji = {
                TeamRole.ADMIN: "👑",
                TeamRole.EDITOR: "✏️",
                TeamRole.AUTHOR: "✍️",
                TeamRole.VIEWER: "👁️"
            }
            emoji = role_emoji.get(member.role, "👤")
            text += f"{emoji} {team.name} ({member.role})\n"
        text += "\n"
    else:
        text += "У тебя пока нет команд.\n\n"
    
    text += "**Доступные действия:**\n"
    text += "• Создать команду\n"
    text += "• Присоединиться к команде\n"
    text += "• Общий контент\n"
    text += "• Утверждение контента\n"
    text += "• Комментарии"
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Создать команду", callback_data="team_create"),
            InlineKeyboardButton("🔍 Найти команду", callback_data="team_find")
        ],
        [
            InlineKeyboardButton("📋 Мои команды", callback_data="team_list"),
            InlineKeyboardButton("📂 Общий контент", callback_data="team_shared_content")
        ],
        [
            InlineKeyboardButton("✅ На утверждение", callback_data="team_pending_approval"),
            InlineKeyboardButton("💬 Комментарии", callback_data="team_comments")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        ]
    ])
    
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def handle_team_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback командной работы"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    if callback_data == "team_create":
        context.user_data['team_create'] = {}
        context.user_data['_conversation_active'] = True
        await query.edit_message_text(
            "➕ **Создание команды**\n\n"
            "Введи название команды:",
            parse_mode="Markdown"
        )
        return "waiting_team_name"
    
    elif callback_data == "team_list":
        with get_db() as db:
            user_teams = db.query(TeamMember).filter(
                TeamMember.user_id == user_id
            ).all()
        
        if not user_teams:
            await query.edit_message_text(
                "📋 **Мои команды**\n\n"
                "Ты пока не состоишь ни в одной команде.\n\n"
                "Создай команду или присоединись к существующей!",
                parse_mode="Markdown"
            )
        else:
            text = "📋 **Мои команды**\n\n"
            keyboard_buttons = []
            
            for member in user_teams[:10]:
                team = member.team
                role_emoji = {
                    TeamRole.ADMIN: "👑",
                    TeamRole.EDITOR: "✏️",
                    TeamRole.AUTHOR: "✍️",
                    TeamRole.VIEWER: "👁️"
                }
                emoji = role_emoji.get(member.role, "👤")
                text += f"{emoji} {team.name} - {member.role}\n"
                keyboard_buttons.append([
                    InlineKeyboardButton(f"{team.name}", callback_data=f"team_view_{team.id}")
                ])
            
            keyboard_buttons.append([
                InlineKeyboardButton("◀️ Назад", callback_data="team_back")
            ])
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                parse_mode="Markdown"
            )
    
    elif callback_data == "team_shared_content":
        await show_shared_content(update, context)
    
    elif callback_data == "team_pending_approval":
        await show_pending_approval(update, context)
    
    elif callback_data == "team_back":
        await show_team_advanced_menu(update, context)
    
    elif callback_data == "main_menu":
        context.user_data.pop('_conversation_active', None)
        await query.edit_message_text("Возврат в главное меню")
        return END
    
    return END


async def show_shared_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает общий контент команды"""
    user_id = update.effective_user.id
    query = update.callback_query if hasattr(update, 'callback_query') else None
    
    with get_db() as db:
        # Получаем команды пользователя
        user_teams = db.query(TeamMember).filter(
            TeamMember.user_id == user_id
        ).all()
        
        if not user_teams:
            text = "📂 **Общий контент**\n\n"
            text += "Ты не состоишь ни в одной команде.\n\n"
            text += "Создай команду или присоединись к существующей!"
            
            if query:
                await query.edit_message_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text(text, parse_mode="Markdown")
            return
        
        # Получаем общий контент из всех команд
        team_ids = [member.team_id for member in user_teams]
        shared_content = db.query(SharedContent).filter(
            SharedContent.team_id.in_(team_ids)
        ).order_by(SharedContent.created_at.desc()).limit(20).all()
        
        if not shared_content:
            text = "📂 **Общий контент**\n\n"
            text += "В твоих командах пока нет общего контента."
            
            if query:
                await query.edit_message_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text(text, parse_mode="Markdown")
            return
        
        text = "📂 **Общий контент команды**\n\n"
        
        for i, item in enumerate(shared_content[:10], 1):
            content = db.query(ContentHistory).filter(
                ContentHistory.id == item.content_history_id
            ).first()
            
            if content:
                content_data = content.content_data if isinstance(content.content_data, dict) else {}
                preview = content_data.get("text", str(content_data))[:50]
                status = "✅ Утвержден" if item.is_approved else "⏳ На утверждении"
                text += f"{i}. {status} - {preview}...\n"
        
        keyboard_buttons = []
        for item in shared_content[:5]:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"📝 Просмотр {item.id}",
                    callback_data=f"team_content_view_{item.id}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton("◀️ Назад", callback_data="team_back")
        ])
        
        if query:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                parse_mode="Markdown"
            )


async def show_pending_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает контент, ожидающий утверждения"""
    user_id = update.effective_user.id
    query = update.callback_query if hasattr(update, 'callback_query') else None
    
    with get_db() as db:
        # Получаем команды, где пользователь может утверждать (ADMIN или EDITOR)
        user_teams = db.query(TeamMember).filter(
            TeamMember.user_id == user_id,
            TeamMember.role.in_([TeamRole.ADMIN.value, TeamRole.EDITOR.value])
        ).all()
        
        if not user_teams:
            text = "✅ **На утверждение**\n\n"
            text += "У тебя нет прав на утверждение контента.\n\n"
            text += "Нужна роль Администратора или Редактора."
            
            if query:
                await query.edit_message_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text(text, parse_mode="Markdown")
            return
        
        team_ids = [member.team_id for member in user_teams]
        pending_content = db.query(SharedContent).filter(
            SharedContent.team_id.in_(team_ids),
            SharedContent.is_approved == False
        ).order_by(SharedContent.created_at.desc()).limit(20).all()
        
        if not pending_content:
            text = "✅ **На утверждение**\n\n"
            text += "Нет контента, ожидающего утверждения."
            
            if query:
                await query.edit_message_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text(text, parse_mode="Markdown")
            return
        
        text = "✅ **Контент на утверждение**\n\n"
        
        keyboard_buttons = []
        for item in pending_content[:10]:
            content = db.query(ContentHistory).filter(
                ContentHistory.id == item.content_history_id
            ).first()
            
            if content:
                content_data = content.content_data if isinstance(content.content_data, dict) else {}
                preview = content_data.get("text", str(content_data))[:50]
                text += f"• {preview}...\n"
                
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        f"✅ Утвердить {item.id}",
                        callback_data=f"team_approve_{item.id}"
                    ),
                    InlineKeyboardButton(
                        f"❌ Отклонить {item.id}",
                        callback_data=f"team_reject_{item.id}"
                    )
                ])
        
        keyboard_buttons.append([
            InlineKeyboardButton("◀️ Назад", callback_data="team_back")
        ])
        
        if query:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                parse_mode="Markdown"
            )


async def handle_team_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия команды"""
    team_name = update.message.text.strip()
    
    if not team_name or len(team_name) < 3:
        await update.message.reply_text(
            "❌ Название слишком короткое. Напиши хотя бы 3 символа:"
        )
        return "waiting_team_name"
    
    context.user_data['team_create']['name'] = team_name
    
    await update.message.reply_text(
        f"✅ Название: {team_name}\n\n"
        "Введи описание команды (опционально) или напиши 'пропустить':"
    )
    
    return "waiting_team_description"


async def handle_team_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания команды и создание"""
    description = update.message.text.strip()
    
    if description.lower() in ['пропустить', 'skip', '']:
        description = None
    
    user_id = update.effective_user.id
    team_name = context.user_data['team_create']['name']
    
    # Создаем команду
    with get_db() as db:
        team = Team(
            name=team_name,
            description=description,
            owner_id=user_id
        )
        db.add(team)
        db.flush()
        
        # Добавляем создателя как администратора
        member = TeamMember(
            team_id=team.id,
            user_id=user_id,
            role=TeamRole.ADMIN.value
        )
        db.add(member)
        db.commit()
    
    await update.message.reply_text(
        f"✅ Команда '{team_name}' создана!\n\n"
        f"Ты добавлен как администратор.\n\n"
        f"Пригласи других участников через ID команды: {team.id}"
    )
    
    context.user_data.pop('team_create', None)
    context.user_data.pop('_conversation_active', None)
    
    return END


async def handle_approve_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка утверждения контента"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("team_approve_"):
        content_id = int(query.data.replace("team_approve_", ""))
        user_id = update.effective_user.id
        
        with get_db() as db:
            shared_content = db.query(SharedContent).filter(
                SharedContent.id == content_id
            ).first()
            
            if not shared_content:
                await query.answer("Контент не найден", show_alert=True)
                return
            
            # Проверяем права
            member = db.query(TeamMember).filter(
                TeamMember.team_id == shared_content.team_id,
                TeamMember.user_id == user_id,
                TeamMember.role.in_([TeamRole.ADMIN.value, TeamRole.EDITOR.value])
            ).first()
            
            if not member:
                await query.answer("У тебя нет прав на утверждение", show_alert=True)
                return
            
            # Утверждаем
            shared_content.is_approved = True
            shared_content.approved_by = user_id
            shared_content.approved_at = datetime.now()
            db.commit()
        
        await query.answer("✅ Контент утвержден!", show_alert=True)
        await show_pending_approval(update, context)
    
    elif query.data.startswith("team_reject_"):
        content_id = int(query.data.replace("team_reject_", ""))
        user_id = update.effective_user.id
        
        with get_db() as db:
            shared_content = db.query(SharedContent).filter(
                SharedContent.id == content_id
            ).first()
            
            if shared_content:
                # Удаляем из общего контента (или помечаем как отклоненный)
                db.delete(shared_content)
                db.commit()
        
        await query.answer("❌ Контент отклонен", show_alert=True)
        await show_pending_approval(update, context)


def setup_team_advanced_handlers(application):
    """Настройка расширенных обработчиков командной работы"""
    # ConversationHandler для создания команды
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_team_callback, pattern="^team_create$"),
        ],
        states={
            "waiting_team_name": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_team_name)
            ],
            "waiting_team_description": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_team_description)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    # Обработчики callback
    from telegram.ext import CallbackQueryHandler
    application.add_handler(
        CallbackQueryHandler(handle_team_callback, pattern="^team_")
    )
    application.add_handler(
        CallbackQueryHandler(handle_approve_content, pattern="^team_approve_|^team_reject_")
    )

