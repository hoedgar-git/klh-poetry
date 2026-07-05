-- Moderator access: a signed-in Supabase Auth user with this email may read all
-- rows and update status (approve/reject). Run once in Supabase SQL Editor.
-- Create the user first: Authentication -> Users -> Add user (check "Auto Confirm").

drop policy if exists comments_admin_all on public.comments;
create policy comments_admin_all on public.comments
  for all to authenticated
  using (auth.jwt() ->> 'email' = 'hoedgar@gmail.com')
  with check (auth.jwt() ->> 'email' = 'hoedgar@gmail.com');

drop policy if exists feedback_admin_all on public.feedback;
create policy feedback_admin_all on public.feedback
  for all to authenticated
  using (auth.jwt() ->> 'email' = 'hoedgar@gmail.com')
  with check (auth.jwt() ->> 'email' = 'hoedgar@gmail.com');
