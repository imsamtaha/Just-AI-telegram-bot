import { table, integer, text, index } from 'sdk/db';
export const turns = table('justai_turns', {
  id: integer('id').primaryKey({autoIncrement:true}), owner: text('owner').notNull(),
  user: text('user_text').notNull(), assistant: text('assistant_text').notNull(),
}, t => ({owner: index('justai_turns_owner').on(t.owner, t.id)}));
export const notes = table('justai_notes', {
  id: integer('id').primaryKey({autoIncrement:true}), owner: text('owner').notNull(), content: text('content').notNull(),
}, t => ({owner: index('justai_notes_owner').on(t.owner, t.id)}));
export const reminders = table('justai_reminders', {
  id: integer('id').primaryKey({autoIncrement:true}), owner: text('owner').notNull(),
  content: text('content').notNull(), due: integer('due').notNull(), status: text('status').notNull().default('pending'),
}, t => ({due: index('justai_reminders_due').on(t.owner, t.status, t.due)}));
export const locks = table('justai_locks', {
  owner: text('owner').primaryKey(), token: text('token').notNull(), until: integer('until_time').notNull(),
});
export const processed = table('justai_processed', {
  id: text('id').primaryKey(), owner: text('owner').notNull(),
});
