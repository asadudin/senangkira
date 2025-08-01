-- Enable UUID generation function if not already enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =================================================================
-- 1. USER & AUTHENTICATION
-- =================================================================

-- Stores user accounts and their company profile information.
CREATE TABLE "auth_user" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "password" VARCHAR(128) NOT NULL,
    "last_login" TIMESTAMPTZ,
    "is_superuser" BOOLEAN NOT NULL DEFAULT FALSE,
    "email" VARCHAR(254) NOT NULL UNIQUE,
    "is_staff" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
    "date_joined" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "company_name" VARCHAR(200),
    "company_address" TEXT,
    "company_logo" VARCHAR(255)  -- Stores a path to the file
);


-- =================================================================
-- 2. CLIENT MANAGEMENT
-- =================================================================

-- Stores information about a user's clients.
CREATE TABLE "clients_client" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(254),
    "phone" VARCHAR(50),
    "address" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "owner_id" UUID NOT NULL REFERENCES "auth_user"("id") ON DELETE CASCADE
);

CREATE INDEX "idx_clients_client_owner_id" ON "clients_client"("owner_id");


-- =================================================================
-- 3. QUOTE & INVOICE WORKFLOW
-- =================================================================

-- Define custom ENUM types for statuses
CREATE TYPE quote_status AS ENUM ('Draft', 'Sent', 'Approved', 'Declined');
CREATE TYPE invoice_status AS ENUM ('Draft', 'Sent', 'Viewed', 'Paid', 'Overdue');

-- Reusable items (services or products) for quick entry
CREATE TABLE "invoicing_item" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "default_price" NUMERIC(10, 2) NOT NULL,
    "owner_id" UUID NOT NULL REFERENCES "auth_user"("id") ON DELETE CASCADE
);

CREATE INDEX "idx_invoicing_item_owner_id" ON "invoicing_item"("owner_id");

-- Quotes Table
CREATE TABLE "invoicing_quote" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "status" quote_status NOT NULL DEFAULT 'Draft',
    "quote_number" VARCHAR(50) NOT NULL,
    "issue_date" DATE NOT NULL DEFAULT CURRENT_DATE,
    "total_amount" NUMERIC(10, 2) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "owner_id" UUID NOT NULL REFERENCES "auth_user"("id") ON DELETE CASCADE,
    "client_id" UUID NOT NULL REFERENCES "clients_client"("id") ON DELETE RESTRICT
);

CREATE TABLE "invoicing_quotelineitem" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "description" TEXT NOT NULL,
    "quantity" NUMERIC(10, 2) NOT NULL,
    "unit_price" NUMERIC(10, 2) NOT NULL,
    "quote_id" UUID NOT NULL REFERENCES "invoicing_quote"("id") ON DELETE CASCADE
);

-- Invoices Table
CREATE TABLE "invoicing_invoice" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "status" invoice_status NOT NULL DEFAULT 'Draft',
    "invoice_number" VARCHAR(50) NOT NULL,
    "issue_date" DATE NOT NULL DEFAULT CURRENT_DATE,
    "due_date" DATE NOT NULL,
    "total_amount" NUMERIC(10, 2) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "owner_id" UUID NOT NULL REFERENCES "auth_user"("id") ON DELETE CASCADE,
    "client_id" UUID NOT NULL REFERENCES "clients_client"("id") ON DELETE RESTRICT,
    "source_quote_id" UUID UNIQUE REFERENCES "invoicing_quote"("id") ON DELETE SET NULL -- Optional link
);

CREATE TABLE "invoicing_invoicelineitem" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "description" TEXT NOT NULL,
    "quantity" NUMERIC(10, 2) NOT NULL,
    "unit_price" NUMERIC(10, 2) NOT NULL,
    "invoice_id" UUID NOT NULL REFERENCES "invoicing_invoice"("id") ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX "idx_invoicing_quote_owner_id" ON "invoicing_quote"("owner_id");
CREATE INDEX "idx_invoicing_invoice_owner_id" ON "invoicing_invoice"("owner_id");
CREATE INDEX "idx_invoicing_invoice_status" ON "invoicing_invoice"("status");
CREATE UNIQUE INDEX "idx_invoicing_quote_owner_number" ON "invoicing_quote"("owner_id", "quote_number");
CREATE UNIQUE INDEX "idx_invoicing_invoice_owner_number" ON "invoicing_invoice"("owner_id", "invoice_number");


-- =================================================================
-- 4. EXPENSE TRACKING
-- =================================================================

-- For simple tracking of money out (cash basis).
CREATE TABLE "expenses_expense" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "description" VARCHAR(255) NOT NULL,
    "amount" NUMERIC(10, 2) NOT NULL,
    "date" DATE NOT NULL,
    "receipt_image" VARCHAR(255), -- Path to the receipt image
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "owner_id" UUID NOT NULL REFERENCES "auth_user"("id") ON DELETE CASCADE
);

CREATE INDEX "idx_expenses_expense_owner_id" ON "expenses_expense"("owner_id");
CREATE INDEX "idx_expenses_expense_date" ON "expenses_expense"("date");