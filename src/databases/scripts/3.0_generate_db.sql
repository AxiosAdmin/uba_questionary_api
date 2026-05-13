CREATE TABLE IF NOT EXISTS institutions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT institutions_pkey PRIMARY KEY (id),
    CONSTRAINT institutions_name_key UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS profiles (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    questions_create_limit INTEGER,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT profiles_pkey PRIMARY KEY (id),
    CONSTRAINT profiles_name_key UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    nickname TEXT NOT NULL,
    password TEXT NOT NULL,
    global_role VARCHAR(50) DEFAULT 'User'::character varying NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS questions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    institution_id UUID NOT NULL,
    topic VARCHAR(100) NOT NULL,
    subtopic TEXT NOT NULL,
    subtopic_description TEXT NOT NULL,
    diversity_mode TEXT NOT NULL,
    question TEXT NOT NULL,
    answer_a TEXT NOT NULL,
    answer_b TEXT NOT NULL,
    answer_c TEXT NOT NULL,
    answer_d TEXT NOT NULL,
    explanation_a TEXT NOT NULL,
    explanation_b TEXT NOT NULL,
    explanation_c TEXT NOT NULL,
    explanation_d TEXT NOT NULL,
    correct_answer CHAR(1) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    answer_e TEXT,
    explanation_e TEXT,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT questions_pkey PRIMARY KEY (id),
    CONSTRAINT questions_correct_answer_check CHECK (
        correct_answer = ANY (ARRAY['A'::bpchar, 'B'::bpchar, 'C'::bpchar, 'D'::bpchar, 'E'::bpchar])
    ),
    CONSTRAINT questions_institution_id_fkey FOREIGN KEY (institution_id) REFERENCES institutions (id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    user_id UUID NOT NULL,
    stripe_subscription_id TEXT NOT NULL,
    status VARCHAR(30) NOT NULL,
    price_id TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    stripe_customer_id TEXT,
    current_period_end TIMESTAMP WITHOUT TIME ZONE,
    questions_generated_in_cycle INTEGER DEFAULT 0 NOT NULL,
    questions_generation_cycle_end TIMESTAMP WITHOUT TIME ZONE,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT subscriptions_pkey PRIMARY KEY (id),
    CONSTRAINT subscriptions_status_check CHECK (
        status::text = ANY (
            ARRAY[
                'active'::character varying,
                'failed_payment'::character varying,
                'canceled'::character varying,
                'incomplete'::character varying,
                'trialing'::character varying
            ]::text[]
        )
    ),
    CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT subscriptions_stripe_subscription_id_key UNIQUE (stripe_subscription_id)
);

CREATE TABLE IF NOT EXISTS users_institutions (
    user_id UUID NOT NULL,
    institution_id UUID NOT NULL,
    profile_id UUID NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT users_institutions_pkey PRIMARY KEY (user_id, institution_id),
    CONSTRAINT users_institutions_institution_id_fkey FOREIGN KEY (institution_id) REFERENCES institutions (id),
    CONSTRAINT users_institutions_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES profiles (id),
    CONSTRAINT users_institutions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS favorite_questions (
    user_id UUID NOT NULL,
    question_id UUID NOT NULL,
    CONSTRAINT favorite_questions_pkey PRIMARY KEY (user_id, question_id),
    CONSTRAINT favorite_questions_question_id_fkey FOREIGN KEY (question_id) REFERENCES questions (id),
    CONSTRAINT favorite_questions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS question_answers (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    user_id UUID NOT NULL,
    question_id UUID NOT NULL,
    answer CHAR(1) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT question_answers_pkey PRIMARY KEY (id),
    CONSTRAINT question_answers_answer_check CHECK (
        answer = ANY (ARRAY['A'::bpchar, 'B'::bpchar, 'C'::bpchar, 'D'::bpchar, 'E'::bpchar])
    ),
    CONSTRAINT question_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES questions (id),
    CONSTRAINT question_answers_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS question_feedbacks (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    question_id UUID NOT NULL,
    is_liked BOOLEAN NOT NULL,
    feedback VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT question_feedbacks_pkey PRIMARY KEY (id),
    CONSTRAINT question_feedbacks_question_id_fkey FOREIGN KEY (question_id) REFERENCES questions (id)
);

CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    user_id UUID NOT NULL,
    text_feedback TEXT NOT NULL,
    CONSTRAINT user_feedback_pkey PRIMARY KEY (id),
    CONSTRAINT user_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id)
);
