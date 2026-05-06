CREATE TABLE IF NOT EXISTS institutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES institutions(id),
    topic character varying(100) NOT NULL,
    subtopic text NOT NULL,
    subtopic_description text NOT NULL,
    diversity_mode text NOT NULL,
    question text NOT NULL,
    answer_a text NOT NULL,
    answer_b text NOT NULL,
    answer_c text NOT NULL,
    answer_d text NOT NULL,
    answer_e text,
    explanation_a text NOT NULL,
    explanation_b text NOT NULL,
    explanation_c text NOT NULL,
    explanation_d text NOT NULL,
    explanation_e text,
    correct_answer character(1) NOT NULL CHECK (correct_answer IN ('A', 'B', 'C', 'D', 'E')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    email text NOT NULL,
    nickname text NOT NULL,
    password text NOT NULL,
    global_role character varying(50) DEFAULT 'User' NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS favorite_questions (
    user_id uuid NOT NULL REFERENCES users(id),
    question_id uuid NOT NULL REFERENCES questions(id),
    PRIMARY KEY (user_id, question_id)
);

CREATE TABLE IF NOT EXISTS question_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id),
    question_id uuid NOT NULL REFERENCES questions(id),
    answer character(1) NOT NULL CHECK (answer IN ('A', 'B', 'C', 'D', 'E')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS question_feedbacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id uuid NOT NULL REFERENCES questions(id),
    is_liked boolean NOT NULL,
    feedback character varying(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    questions_create_limit integer,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS users_institutions (
    user_id uuid NOT NULL REFERENCES users(id),
    institution_id uuid NOT NULL REFERENCES institutions(id),
    profile_id uuid NOT NULL REFERENCES profiles(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL,
    PRIMARY KEY (user_id, institution_id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    stripe_subscription_id TEXT UNIQUE NOT NULL,
    stripe_customer_id TEXT,
    status VARCHAR(30) NOT NULL CHECK (status IN ( 'active', 'failed_payment', 'canceled', 'incomplete', 'trialing')),
    price_id TEXT NOT NULL,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);