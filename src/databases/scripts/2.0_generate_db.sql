-- Script para criar as tabelas do banco de dados

-- Tabela de perfis
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    questions_create_limit INTEGER NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

-- Tabela de usuários
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    nickname TEXT NOT NULL,
    password TEXT NOT NULL,
    global_role VARCHAR(50) NOT NULL DEFAULT 'User',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

-- Tabela de instituições
CREATE TABLE IF NOT EXISTS institutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

-- Tabela de associação entre usuários, instituições e perfis
CREATE TABLE IF NOT EXISTS users_institutions (
    user_id UUID REFERENCES users(id),
    institution_id UUID REFERENCES institutions(id),
    profile_id UUID REFERENCES profiles(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL,
    PRIMARY KEY (user_id, institution_id)
);

-- Tabela de questões
CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES institutions(id) NOT NULL,
    topic VARCHAR(100) NOT NULL,
    subject TEXT NOT NULL,
    question TEXT NOT NULL,
    answer_a TEXT NOT NULL,
    answer_b TEXT NOT NULL,
    answer_c TEXT NOT NULL,
    answer_d TEXT NOT NULL,
    answer_e TEXT,
    explanation_a TEXT NOT NULL,
    explanation_b TEXT NOT NULL,
    explanation_c TEXT NOT NULL,
    explanation_d TEXT NOT NULL,
    explanation_e TEXT,
    correct_answer CHAR(1) NOT NULL CHECK (correct_answer IN ('A', 'B', 'C', 'D')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

-- Tabela de respostas das questões pelos usuários
CREATE TABLE IF NOT EXISTS question_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    question_id UUID REFERENCES questions(id),
    answer CHAR(1) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

-- Tabela de feedbacks das questões pelos usuários
CREATE TABLE IF NOT EXISTS question_feedbacks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID REFERENCES questions(id),
  is_liked BOOLEAN NOT NULL,
  feedback VARCHAR(100) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NULL
);

-- Tabela de questões favoritas dos usuários
CREATE TABLE IF NOT EXISTS favorite_questions (
    user_id UUID REFERENCES users(id),
    question_id UUID REFERENCES questions(id),
    PRIMARY KEY (user_id, question_id)
);
