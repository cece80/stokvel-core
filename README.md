# Stokvel OS Web Platform

> **Multi-tenant group economy system for stokvel coordination, commerce, and financial management**

---

## Web App Architecture (Simplified but Complete)

> **Stokvel OS Web Platform (multi-tenant group economy system)**

---

## 1. Frontend (Web App)

### Recommended Stack

- Next.js (React)
- Tailwind CSS
- React Query / TanStack Query

### Pages Structure

#### Auth
- `/login` (phone/email OTP)
- `/verify-otp`

#### Organization (Tenant Root)
- `/org/create`
- `/org/select`

#### Stokvel
- `/stokvels`
- `/stokvel/:id`
- `/stokvel/:id/members`
- `/stokvel/:id/contributions`
- `/stokvel/:id/voting`

#### Deals (Core Feature)
- `/deals`
- `/deal/:id`
- `/deal/:id/join`

#### Wallet
- `/wallet`
- `/transactions`

#### Governance
- `/votes`
- `/rules`

#### Disputes
- `/disputes`

#### Admin Dashboard
- `/admin`

---

## 2. Frontend State Rule (Critical)

Every request must carry:

```ts
organization_id
stokvel_id // if inside stokvel context
```

---

## 3. Backend Structure (Modular Monolith)

Instead of microservices (for now), use a **modular monolith**.

### Suggested Backend Stack
- Node.js (NestJS or Express)
- PostgreSQL
- Redis (sessions + caching)

### Modules

#### 1. Auth Module
- OTP login (email + phone)
- JWT sessions

#### 2. Organization Module
- Create org
- Switch org
- Tenant isolation

#### 3. Stokvel Module
- Create stokvel
- Join stokvel
- Manage members
- Contributions

#### 4. Deal Module
- List deals
- Join deal
- Aggregate demand
- Connect to Saleor

#### 5. Finance Module
- Ledger entries
- Wallets
- Escrow logic

#### 6. Voting Module
- Vote creation
- Vote tally
- Decision engine

#### 7. Dispute Module
- Raise dispute
- Freeze transaction
- Resolve

#### 8. Notification Module
- Email
- SMS
- In-app alerts

#### 9. Risk Module
- Fraud detection
- Flags
- Scoring

---

## 4. Money Flow (Simplified)

You are NOT a bank. The flow is:

```
User -> Payment Provider -> Ledger -> Wallet -> Escrow -> Release
```

Payment providers:
- Ozow
- Paystack

---

## 5. Commerce (Saleor Integration)

### Flow
1. Deal created in your app
2. Sync product to Saleor
3. Saleor handles: inventory, checkout
4. Your app handles: stokvel logic, voting, grouping

---

## 6. Multi-Tenancy (Critical)

Every table and request includes:

```sql
organization_id
```

### Rule
```
IF request.organization_id != user.organization_id:
   deny_access
```

---

## 7. Core Database Layer

### Key Simplification
- NO microservice split yet
- ONE database
- Modular backend structure

---

## 8. Event System (Light Version)

Instead of Kafka, use internal event bus:

```ts
eventEmitter.emit("deal_approved")
```

### Events
- `user_joined`
- `stokvel_created`
- `contribution_paid`
- `deal_joined`
- `vote_cast`
- `deal_approved`
- `payment_released`

---

## 9. Auth Flow

### Login
1. Enter phone/email
2. Send OTP
3. Verify OTP
4. Issue JWT

### Middleware
```
IF token_invalid:
   block_request
```

---

## 10. Stokvel Flow

### Create Stokvel
- Set goal
- Set rules
- Invite members

### Join Stokvel
- Accept invite
- Assign role

### Contributions
- Record payment
- Update ledger

### Voting
- Cast vote
- Check quorum
- Approve/reject

---

## 11. Deal Flow (Core System)

1. Supplier adds product
2. System wraps it as "Deal"
3. Stokvels join
4. Demand aggregates
5. Price unlocks
6. Vote happens
7. If approved -> order sent to Saleor
8. Payment processed
9. Delivery confirmed
10. Funds released

---

## 12. Fraud Logic

### Rules
- No single-admin control
- Voting required for spend
- Audit logs for everything
- Duplicate transaction prevention

---

## 13. Admin Panel

### Admin Can
- View all stokvels
- Freeze accounts
- Manage disputes
- View analytics
- Monitor fraud

---

## 14. Deployment

- **Frontend:** Vercel
- **Backend:** Render / AWS / DigitalOcean
- **Database:** PostgreSQL
- **Cache:** Upstash or Redis Cloud

---

## External Systems
- Saleor (commerce)
- Ozow (payments)
- Paystack (payments)

---

## Summary

This web app is a **multi-tenant stokvel coordination + commerce + financial system** -- combining e-commerce, fintech, and marketplace concepts, all controlled by **stokvel logic**.
