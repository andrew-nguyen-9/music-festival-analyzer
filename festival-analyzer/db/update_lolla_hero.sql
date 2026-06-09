-- Run this in the Supabase SQL editor to set Lollapalooza's hero/city image
-- on an ALREADY-seeded database (no need to re-run the full seed).
update festivals
set hero_image_url = 'https://images.unsplash.com/photo-1631548637245-043803a8b776?q=80&w=987&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'
where slug = 'lollapalooza';
