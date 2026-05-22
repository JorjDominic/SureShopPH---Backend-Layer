-- Migration 0003: Add notes and raw_data columns to scan_history
-- Run this in Supabase SQL Editor before deploying backend changes.

alter table public.scan_history
    add column if not exists notes    text,
    add column if not exists raw_data jsonb;
