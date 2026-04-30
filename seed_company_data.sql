-- ============================================================
-- Talk-to-DB | Company-level seed  (100+ rows)
-- ============================================================

-- ── Schema ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS departments (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    budget      DECIMAL(14,2),
    location    VARCHAR(100),
    head_count  INT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS employees (
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(100) NOT NULL,
    email             VARCHAR(150) UNIQUE,
    salary            DECIMAL(10,2),
    department        VARCHAR(50),
    department_id     INT REFERENCES departments(id),
    role              VARCHAR(80),
    hire_date         DATE,
    is_active         BOOLEAN DEFAULT TRUE,
    performance_score DECIMAL(3,1),
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customers (
    id           SERIAL PRIMARY KEY,
    company_name VARCHAR(150),
    contact_name VARCHAR(100),
    email        VARCHAR(150),
    phone        VARCHAR(30),
    country      VARCHAR(60),
    tier         VARCHAR(20) DEFAULT 'standard',
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(150) NOT NULL,
    category   VARCHAR(80),
    unit_price DECIMAL(10,2),
    stock_qty  INT DEFAULT 0,
    is_active  BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    order_id     SERIAL PRIMARY KEY,
    customer_id  INT REFERENCES customers(id),
    product_id   INT REFERENCES products(id),
    product      VARCHAR(100),
    revenue      DECIMAL(10,2),
    quantity     INT,
    discount_pct DECIMAL(5,2) DEFAULT 0,
    order_date   DATE DEFAULT CURRENT_DATE,
    status       VARCHAR(30) DEFAULT 'completed'
);

CREATE TABLE IF NOT EXISTS projects (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(150) NOT NULL,
    department_id INT REFERENCES departments(id),
    budget        DECIMAL(14,2),
    spent         DECIMAL(14,2) DEFAULT 0,
    status        VARCHAR(30) DEFAULT 'active',
    start_date    DATE,
    end_date      DATE,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoices (
    id          SERIAL PRIMARY KEY,
    order_id    INT REFERENCES orders(order_id),
    customer_id INT REFERENCES customers(id),
    amount      DECIMAL(10,2),
    tax         DECIMAL(10,2),
    total       DECIMAL(10,2),
    paid        BOOLEAN DEFAULT FALSE,
    due_date    DATE,
    issued_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS support_tickets (
    id          SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    assigned_to INT REFERENCES employees(id),
    subject     VARCHAR(200),
    priority    VARCHAR(20) DEFAULT 'medium',
    status      VARCHAR(30) DEFAULT 'open',
    created_at  TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- ── Truncate ─────────────────────────────────────────────────
TRUNCATE TABLE support_tickets, invoices, orders, projects,
              employees, products, customers, departments
RESTART IDENTITY CASCADE;

-- ── Departments (8 rows) ─────────────────────────────────────
INSERT INTO departments (name, budget, location, head_count, created_at) VALUES
  ('Engineering',       4500000.00, 'Bengaluru',  42, '2019-01-15'),
  ('Product',           1800000.00, 'Bengaluru',  18, '2019-02-01'),
  ('Marketing',         1200000.00, 'Mumbai',     15, '2019-03-10'),
  ('Sales',             2000000.00, 'Delhi',      30, '2019-03-10'),
  ('Human Resources',    600000.00, 'Bengaluru',   8, '2019-04-01'),
  ('Finance',            800000.00, 'Mumbai',     10, '2019-04-15'),
  ('Customer Success',   900000.00, 'Hyderabad',  20, '2020-01-10'),
  ('Data & Analytics',  1100000.00, 'Bengaluru',  12, '2021-06-01');

-- ── Employees (40 rows) ──────────────────────────────────────
INSERT INTO employees (name,email,salary,department,department_id,role,hire_date,is_active,performance_score,created_at) VALUES
  ('Alice Sharma',    'alice@corp.io',    120000,'Engineering',      1,'Senior Engineer',       '2020-01-10',TRUE, 9.2,'2020-01-10'),
  ('Bob Menon',       'bob@corp.io',       95000,'Engineering',      1,'Backend Engineer',      '2020-06-15',TRUE, 7.8,'2020-06-15'),
  ('Carol Jain',      'carol@corp.io',    145000,'Engineering',      1,'Engineering Manager',   '2019-03-01',TRUE, 9.5,'2019-03-01'),
  ('Dave Kumar',      'dave@corp.io',      72000,'Marketing',        3,'Content Strategist',    '2021-02-20',TRUE, 7.0,'2021-02-20'),
  ('Eve Pillai',      'eve@corp.io',      110000,'Product',          2,'Senior PM',             '2019-11-05',TRUE, 8.9,'2019-11-05'),
  ('Frank Thomas',    'frank@corp.io',     68000,'Sales',            4,'Sales Executive',       '2022-04-01',TRUE, 7.5,'2022-04-01'),
  ('Grace Nair',      'grace@corp.io',     85000,'Sales',            4,'Sales Lead',            '2021-07-15',TRUE, 8.3,'2021-07-15'),
  ('Hira Bose',       'hira@corp.io',      78000,'Human Resources',  5,'HR Business Partner',  '2020-09-10',TRUE, 8.0,'2020-09-10'),
  ('Ivan Rao',        'ivan@corp.io',     130000,'Data & Analytics', 8,'Data Scientist',        '2021-06-01',TRUE, 9.1,'2021-06-01'),
  ('Julia Desai',     'julia@corp.io',     92000,'Finance',          6,'Financial Analyst',     '2020-03-22',TRUE, 8.4,'2020-03-22'),
  ('Kiran Seth',      'kiran@corp.io',     58000,'Customer Success', 7,'Support Specialist',   '2022-08-01',TRUE, 7.2,'2022-08-01'),
  ('Leena Patel',     'leena@corp.io',    115000,'Engineering',      1,'DevOps Engineer',       '2021-01-18',TRUE, 8.7,'2021-01-18'),
  ('Mohan Gupta',     'mohan@corp.io',     62000,'Marketing',        3,'Growth Marketer',       '2022-05-10',TRUE, 7.3,'2022-05-10'),
  ('Nisha Verma',     'nisha@corp.io',    105000,'Product',          2,'Product Manager',       '2020-11-30',TRUE, 8.6,'2020-11-30'),
  ('Omar Sheikh',     'omar@corp.io',      88000,'Sales',            4,'Account Manager',       '2021-09-14',TRUE, 8.1,'2021-09-14'),
  ('Priya Choudhury', 'priya@corp.io',     75000,'Data & Analytics', 8,'Data Analyst',          '2022-02-07',TRUE, 8.0,'2022-02-07'),
  ('Raj Agarwal',     'raj@corp.io',       55000,'Finance',          6,'Accounts Executive',    '2023-01-05',TRUE, 6.9,'2023-01-05'),
  ('Sneha Reddy',     'sneha@corp.io',     98000,'Engineering',      1,'Full-Stack Engineer',   '2021-08-22',TRUE, 8.5,'2021-08-22'),
  ('Tarun Mehta',     'tarun@corp.io',     48000,'Customer Success', 7,'Customer Success Rep',  '2023-03-15',FALSE,6.5,'2023-03-15'),
  ('Uma Krishnan',    'uma@corp.io',      140000,'Data & Analytics', 8,'Head of Analytics',     '2021-06-01',TRUE, 9.4,'2021-06-01'),
  ('Vikram Singh',    'vikram@corp.io',   125000,'Engineering',      1,'Platform Engineer',     '2020-08-03',TRUE, 8.8,'2020-08-03'),
  ('Wren Lopez',      'wren@corp.io',      70000,'Marketing',        3,'SEO Specialist',        '2022-09-01',TRUE, 7.1,'2022-09-01'),
  ('Xara Mendes',     'xara@corp.io',      90000,'Product',          2,'UX Designer',           '2021-05-11',TRUE, 8.4,'2021-05-11'),
  ('Yash Tiwari',     'yash@corp.io',      65000,'Sales',            4,'Sales Executive',       '2023-02-14',TRUE, 7.0,'2023-02-14'),
  ('Zara Khan',       'zara@corp.io',      82000,'Customer Success', 7,'Customer Success Lead', '2021-10-20',TRUE, 8.5,'2021-10-20'),
  ('Arun Das',        'arun@corp.io',      77000,'Finance',          6,'Senior Accountant',     '2020-07-07',TRUE, 8.2,'2020-07-07'),
  ('Bhavna Iyer',     'bhavna@corp.io',   108000,'Engineering',      1,'QA Lead',               '2021-03-25',TRUE, 8.6,'2021-03-25'),
  ('Chetan Soni',     'chetan@corp.io',    60000,'Human Resources',  5,'Recruiter',             '2022-06-01',TRUE, 7.4,'2022-06-01'),
  ('Divya Sharma',    'divya@corp.io',     95000,'Data & Analytics', 8,'ML Engineer',           '2022-03-10',TRUE, 8.9,'2022-03-10'),
  ('Eshan Kapoor',    'eshan@corp.io',     85000,'Sales',            4,'Senior Sales Exec',     '2020-12-01',TRUE, 8.3,'2020-12-01'),
  ('Farhan Qureshi',  'farhan@corp.io',    73000,'Marketing',        3,'Brand Manager',         '2021-11-15',TRUE, 7.7,'2021-11-15'),
  ('Gita Rao',        'gita@corp.io',      68000,'Customer Success', 7,'Support Engineer',      '2022-07-20',TRUE, 7.5,'2022-07-20'),
  ('Harsh Malhotra',  'harsh@corp.io',    135000,'Engineering',      1,'Solutions Architect',   '2019-09-01',TRUE, 9.3,'2019-09-01'),
  ('Ishita Kaur',     'ishita@corp.io',    80000,'Product',          2,'Product Analyst',       '2022-01-17',TRUE, 7.9,'2022-01-17'),
  ('Jai Prakash',     'jai@corp.io',       55000,'Finance',          6,'Payroll Specialist',    '2023-04-01',TRUE, 6.8,'2023-04-01'),
  ('Kavita Nair',     'kavita@corp.io',   100000,'Engineering',      1,'Backend Lead',          '2020-05-18',TRUE, 8.7,'2020-05-18'),
  ('Lakshmi Pillai',  'lakshmi@corp.io',   72000,'Human Resources',  5,'HR Manager',            '2019-08-15',TRUE, 8.5,'2019-08-15'),
  ('Mihir Shah',      'mihir@corp.io',     88000,'Data & Analytics', 8,'BI Developer',          '2021-09-05',TRUE, 8.0,'2021-09-05'),
  ('Neha Bansal',     'neha@corp.io',      93000,'Product',          2,'Technical PM',          '2020-04-27',TRUE, 8.8,'2020-04-27'),
  ('Omkar Patil',     'omkar@corp.io',     67000,'Sales',            4,'Inside Sales Rep',      '2023-06-01',TRUE, 7.0,'2023-06-01');

-- ── Customers (20 rows) ──────────────────────────────────────
INSERT INTO customers (company_name,contact_name,email,phone,country,tier,created_at) VALUES
  ('Nexus Retail Ltd',      'Arjun Sood',     'arjun@nexus.com',      '+91-9810001001','India',       'enterprise','2021-01-20'),
  ('TechWave Solutions',    'Sara Collins',   'sara@techwave.io',     '+1-415-5550001','USA',          'enterprise','2021-03-05'),
  ('BlueStar Corp',         'Yuki Tanaka',    'yuki@bluestar.co',     '+81-3-1234-5678','Japan',       'pro',       '2021-07-14'),
  ('Meridian Logistics',    'Laura Gomez',    'lgomez@meridian.es',   '+34-91-5550023','Spain',        'pro',       '2022-01-08'),
  ('Orion Healthcare',      'David Park',     'dpark@orionhc.com',    '+1-212-5550042','USA',          'enterprise','2022-04-12'),
  ('Sunrise Fintech',       'Aisha Patel',    'aisha@sunriseft.in',   '+91-9820001002','India',        'pro',       '2022-06-30'),
  ('GreenLeaf Agritech',    'Carlos Mota',    'cmota@greenleaf.br',   '+55-11-5550078','Brazil',       'standard',  '2022-09-17'),
  ('Alpine Travel Group',   'Frida Lund',     'frida@alpine.no',      '+47-22-5550099','Norway',       'standard',  '2023-01-25'),
  ('PeakEdge Analytics',    'Ming Zhao',      'mzhao@peakedge.cn',    '+86-10-8888-0001','China',      'pro',       '2023-03-10'),
  ('Bolt Commerce',         'Rania Hassan',   'rania@boltco.ae',      '+971-4-5550112','UAE',          'enterprise','2023-05-22'),
  ('Vertex Consulting',     'James Osei',     'josei@vertex.gh',      '+233-30-5550031','Ghana',       'standard',  '2023-07-01'),
  ('Nimbus Cloud',          'Elena Kovac',    'ekovac@nimbus.si',     '+386-1-5550050','Slovenia',     'pro',       '2023-08-14'),
  ('IronTree Infra',        'Ahmed Al-Sayed', 'ahmed@irontree.sa',    '+966-11-5550060','Saudi Arabia','enterprise','2023-09-05'),
  ('Coastal Media',         'Preethi Nair',   'preethi@coastal.in',   '+91-9830001003','India',        'standard',  '2023-10-10'),
  ('SkyNet Logistics',      'Brian Tong',     'btong@skynet.sg',      '+65-6555-0010','Singapore',    'pro',       '2023-11-20'),
  ('Fortis Pharma',         'Maya Sharma',    'maya@fortispharma.in', '+91-9840001004','India',        'enterprise','2024-01-08'),
  ('RedRock Mining',        'Luke Dawson',    'ldawson@redrock.au',   '+61-2-5550070','Australia',    'standard',  '2024-02-15'),
  ('SwiftPay Fintech',      'Olu Adeyemi',    'olu@swiftpay.ng',      '+234-1-5550080','Nigeria',      'pro',       '2024-03-22'),
  ('ClearPath EdTech',      'Suresh Nair',    'suresh@clearpath.in',  '+91-9850001005','India',        'standard',  '2024-04-10'),
  ('GlobalMart Retail',     'Ana Lima',       'ana@globalmart.br',    '+55-21-5550090','Brazil',       'enterprise','2024-05-18');

-- ── Products (12 rows) ───────────────────────────────────────
INSERT INTO products (name,category,unit_price,stock_qty,is_active,created_at) VALUES
  ('DataLens Pro',        'Analytics SaaS', 1200.00, 999,TRUE,'2020-06-01'),
  ('DataLens Starter',    'Analytics SaaS',  299.00, 999,TRUE,'2020-06-01'),
  ('CloudVault Storage',  'Infrastructure',  499.00, 500,TRUE,'2021-01-15'),
  ('SecureID Gateway',    'Security',       1800.00, 200,TRUE,'2021-03-01'),
  ('InsightBoard',        'BI & Reporting',  750.00, 400,TRUE,'2021-09-10'),
  ('AutoPilot CRM',       'CRM Platform',   2200.00, 150,TRUE,'2022-02-20'),
  ('NeuralChat AI',       'AI/ML Services', 3500.00,  80,TRUE,'2022-07-01'),
  ('FlowSync API',        'Integration',     350.00, 999,TRUE,'2022-11-05'),
  ('ReportMagic',         'BI & Reporting',  180.00, 999,TRUE,'2023-01-01'),
  ('Compliance Shield',   'Security',       2800.00,  60,TRUE,'2023-04-15'),
  ('DataLens Enterprise', 'Analytics SaaS', 4500.00,  50,TRUE,'2023-09-01'),
  ('AIWorkflow Suite',    'AI/ML Services', 5200.00,  30,TRUE,'2024-01-10');

-- ── Orders (50 rows) ─────────────────────────────────────────
INSERT INTO orders (customer_id,product_id,product,revenue,quantity,discount_pct,order_date,status) VALUES
  ( 1, 1,'DataLens Pro',        12000.00,10, 0.00,'2024-01-10','completed'),
  ( 2, 6,'AutoPilot CRM',       22000.00,10, 5.00,'2024-01-18','completed'),
  ( 3, 4,'SecureID Gateway',     9000.00, 5, 0.00,'2024-02-02','completed'),
  ( 4, 5,'InsightBoard',         7500.00,10, 0.00,'2024-02-14','completed'),
  ( 5, 7,'NeuralChat AI',       35000.00,10, 3.00,'2024-03-05','completed'),
  ( 6, 2,'DataLens Starter',     2990.00,10, 0.00,'2024-03-20','completed'),
  ( 7, 3,'CloudVault Storage',   2495.00, 5, 0.00,'2024-04-01','completed'),
  ( 8, 8,'FlowSync API',         1750.00, 5, 0.00,'2024-04-22','completed'),
  ( 9, 9,'ReportMagic',           900.00, 5, 0.00,'2024-05-08','completed'),
  (10,10,'Compliance Shield',    14000.00, 5, 0.00,'2024-05-30','completed'),
  ( 1, 7,'NeuralChat AI',        17500.00, 5, 0.00,'2024-07-12','completed'),
  ( 2, 1,'DataLens Pro',         14400.00,12, 0.00,'2024-08-03','completed'),
  ( 5,10,'Compliance Shield',    28000.00,10, 0.00,'2024-09-19','completed'),
  ( 3, 6,'AutoPilot CRM',        11000.00, 5, 0.00,'2024-10-07','completed'),
  ( 6, 5,'InsightBoard',          3750.00, 5, 0.00,'2024-11-15','completed'),
  ( 4, 7,'NeuralChat AI',        70000.00,20, 5.00,'2024-12-01','completed'),
  (10, 1,'DataLens Pro',         60000.00,50, 0.00,'2025-01-10','completed'),
  ( 1, 6,'AutoPilot CRM',        22000.00,10, 0.00,'2025-01-25','completed'),
  ( 9, 4,'SecureID Gateway',     18000.00,10, 0.00,'2025-02-14','completed'),
  ( 2, 7,'NeuralChat AI',        35000.00,10, 0.00,'2025-03-01','completed'),
  ( 7, 9,'ReportMagic',           1800.00,10, 0.00,'2025-03-18','completed'),
  ( 8, 3,'CloudVault Storage',    4990.00,10, 0.00,'2025-04-02','completed'),
  ( 5, 1,'DataLens Pro',         24000.00,20, 0.00,'2025-04-20','completed'),
  ( 3, 5,'InsightBoard',          7500.00,10, 0.00,'2025-05-05','completed'),
  ( 6, 8,'FlowSync API',          3500.00,10, 0.00,'2025-05-22','completed'),
  (11, 2,'DataLens Starter',      2990.00,10, 0.00,'2024-06-01','completed'),
  (12, 5,'InsightBoard',          7500.00,10, 0.00,'2024-06-15','completed'),
  (13,11,'DataLens Enterprise',  45000.00,10, 0.00,'2024-07-01','completed'),
  (14, 8,'FlowSync API',          1750.00, 5, 0.00,'2024-07-20','completed'),
  (15, 3,'CloudVault Storage',    2495.00, 5, 0.00,'2024-08-10','completed'),
  (16,12,'AIWorkflow Suite',     52000.00,10, 0.00,'2024-08-25','completed'),
  (17, 9,'ReportMagic',            900.00, 5, 0.00,'2024-09-05','completed'),
  (18, 1,'DataLens Pro',         12000.00,10, 0.00,'2024-09-22','completed'),
  (19, 2,'DataLens Starter',      2990.00,10, 0.00,'2024-10-08','completed'),
  (20,11,'DataLens Enterprise',  90000.00,20, 5.00,'2024-10-25','completed'),
  (11, 6,'AutoPilot CRM',        22000.00,10, 0.00,'2024-11-01','completed'),
  (12, 4,'SecureID Gateway',      9000.00, 5, 0.00,'2024-11-18','completed'),
  (13, 7,'NeuralChat AI',        35000.00,10, 0.00,'2024-12-05','completed'),
  (14,10,'Compliance Shield',    14000.00, 5, 0.00,'2024-12-20','completed'),
  (15,12,'AIWorkflow Suite',     26000.00, 5, 0.00,'2025-01-05','completed'),
  (16, 1,'DataLens Pro',         24000.00,20, 0.00,'2025-01-20','completed'),
  (17, 5,'InsightBoard',          3750.00, 5, 0.00,'2025-02-01','completed'),
  (18, 7,'NeuralChat AI',        17500.00, 5, 0.00,'2025-02-18','completed'),
  (19, 3,'CloudVault Storage',    2495.00, 5, 0.00,'2025-03-05','completed'),
  (20, 6,'AutoPilot CRM',        22000.00,10, 0.00,'2025-03-22','completed'),
  ( 5,12,'AIWorkflow Suite',     52000.00,10, 0.00,'2025-04-05','completed'),
  ( 2,11,'DataLens Enterprise',  45000.00,10, 0.00,'2025-04-18','completed'),
  (10, 7,'NeuralChat AI',        35000.00,10, 2.00,'2025-05-02','completed'),
  ( 1,12,'AIWorkflow Suite',     52000.00,10, 0.00,'2025-05-15','completed'),
  ( 3,11,'DataLens Enterprise',  45000.00,10, 0.00,'2025-05-28','completed');


-- ── Projects (12 rows) ───────────────────────────────────────
INSERT INTO projects (name,department_id,budget,spent,status,start_date,end_date,created_at) VALUES
  ('Platform v3 Rewrite',         1,1500000.00,1120000.00,'active',   '2024-01-01','2025-06-30','2023-12-01'),
  ('AI Feature Rollout',          1, 800000.00, 650000.00,'active',   '2024-04-01','2025-03-31','2024-03-01'),
  ('Brand Refresh 2025',          3, 250000.00, 230000.00,'completed','2024-01-15','2024-12-31','2024-01-01'),
  ('CRM Migration',               4, 400000.00, 180000.00,'active',   '2024-07-01','2025-07-01','2024-06-01'),
  ('HR System Upgrade',           5, 150000.00, 148000.00,'completed','2023-06-01','2024-05-31','2023-05-15'),
  ('Annual Financial Audit',      6,  80000.00,  75000.00,'completed','2025-01-01','2025-03-31','2024-12-01'),
  ('Customer Health Dashboard',   7, 200000.00,  90000.00,'active',   '2024-10-01','2025-09-30','2024-09-01'),
  ('Data Lakehouse Build-out',    8, 600000.00, 310000.00,'active',   '2024-03-01','2025-12-31','2024-02-15'),
  ('Zero-Trust Security Program', 1, 350000.00, 200000.00,'active',   '2024-06-01','2025-06-01','2024-05-15'),
  ('Market Expansion APAC',       4, 500000.00, 120000.00,'active',   '2025-01-01','2026-01-01','2024-12-01'),
  ('Internal BI Modernisation',   8, 280000.00, 180000.00,'active',   '2024-09-01','2025-08-31','2024-08-15'),
  ('Compliance & Audit FY26',     6, 120000.00,  10000.00,'active',   '2025-04-01','2026-03-31','2025-03-15');

-- ── Invoices (50 rows, one per order) ────────────────────────
INSERT INTO invoices (order_id,customer_id,amount,tax,total,paid,due_date,issued_at) VALUES
  ( 1, 1, 12000.00, 2160.00, 14160.00,TRUE, '2024-02-09','2024-01-10'),
  ( 2, 2, 20900.00, 3762.00, 24662.00,TRUE, '2024-02-17','2024-01-18'),
  ( 3, 3,  9000.00, 1620.00, 10620.00,TRUE, '2024-03-03','2024-02-02'),
  ( 4, 4,  7500.00, 1350.00,  8850.00,TRUE, '2024-03-15','2024-02-14'),
  ( 5, 5, 33950.00, 6111.00, 40061.00,TRUE, '2024-04-04','2024-03-05'),
  ( 6, 6,  2990.00,  538.20,  3528.20,TRUE, '2024-04-19','2024-03-20'),
  ( 7, 7,  2495.00,  449.10,  2944.10,TRUE, '2024-05-01','2024-04-01'),
  ( 8, 8,  1750.00,  315.00,  2065.00,TRUE, '2024-05-22','2024-04-22'),
  ( 9, 9,   900.00,  162.00,  1062.00,TRUE, '2024-06-07','2024-05-08'),
  (10,10, 14000.00, 2520.00, 16520.00,TRUE, '2024-06-29','2024-05-30'),
  (11, 1, 17500.00, 3150.00, 20650.00,TRUE, '2024-08-11','2024-07-12'),
  (12, 2, 14400.00, 2592.00, 16992.00,TRUE, '2024-09-02','2024-08-03'),
  (13, 5, 28000.00, 5040.00, 33040.00,TRUE, '2024-10-19','2024-09-19'),
  (14, 3, 11000.00, 1980.00, 12980.00,TRUE, '2024-11-06','2024-10-07'),
  (15, 6,  3750.00,  675.00,  4425.00,TRUE, '2024-12-15','2024-11-15'),
  (16, 4, 66500.00,11970.00, 78470.00,FALSE,'2025-01-01','2024-12-01'),
  (17,10, 60000.00,10800.00, 70800.00,TRUE, '2025-02-09','2025-01-10'),
  (18, 1, 22000.00, 3960.00, 25960.00,TRUE, '2025-02-24','2025-01-25'),
  (19, 9, 18000.00, 3240.00, 21240.00,FALSE,'2025-03-16','2025-02-14'),
  (20, 2, 35000.00, 6300.00, 41300.00,TRUE, '2025-03-31','2025-03-01'),
  (21, 7,  1800.00,  324.00,  2124.00,TRUE, '2025-04-17','2025-03-18'),
  (22, 8,  4990.00,  898.20,  5888.20,TRUE, '2025-05-02','2025-04-02'),
  (23, 5, 24000.00, 4320.00, 28320.00,FALSE,'2025-05-20','2025-04-20'),
  (24, 3,  7500.00, 1350.00,  8850.00,TRUE, '2025-06-04','2025-05-05'),
  (25, 6,  3500.00,  630.00,  4130.00,TRUE, '2025-06-21','2025-05-22'),
  (26,11,  2990.00,  538.20,  3528.20,TRUE, '2024-07-01','2024-06-01'),
  (27,12,  7500.00, 1350.00,  8850.00,TRUE, '2024-07-15','2024-06-15'),
  (28,13, 45000.00, 8100.00, 53100.00,TRUE, '2024-08-01','2024-07-01'),
  (29,14,  1750.00,  315.00,  2065.00,TRUE, '2024-08-20','2024-07-20'),
  (30,15,  2495.00,  449.10,  2944.10,TRUE, '2024-09-09','2024-08-10'),
  (31,16, 52000.00, 9360.00, 61360.00,TRUE, '2024-09-24','2024-08-25'),
  (32,17,   900.00,  162.00,  1062.00,TRUE, '2024-10-05','2024-09-05'),
  (33,18, 12000.00, 2160.00, 14160.00,TRUE, '2024-10-22','2024-09-22'),
  (34,19,  2990.00,  538.20,  3528.20,TRUE, '2024-11-07','2024-10-08'),
  (35,20, 85500.00,15390.00,100890.00,TRUE, '2024-11-24','2024-10-25'),
  (36,11, 22000.00, 3960.00, 25960.00,FALSE,'2024-12-01','2024-11-01'),
  (37,12,  9000.00, 1620.00, 10620.00,TRUE, '2024-12-18','2024-11-18'),
  (38,13, 35000.00, 6300.00, 41300.00,TRUE, '2025-01-04','2024-12-05'),
  (39,14, 14000.00, 2520.00, 16520.00,TRUE, '2025-01-19','2024-12-20'),
  (40,15, 26000.00, 4680.00, 30680.00,TRUE, '2025-02-04','2025-01-05'),
  (41,16, 24000.00, 4320.00, 28320.00,TRUE, '2025-02-19','2025-01-20'),
  (42,17,  3750.00,  675.00,  4425.00,TRUE, '2025-03-03','2025-02-01'),
  (43,18, 17500.00, 3150.00, 20650.00,FALSE,'2025-03-20','2025-02-18'),
  (44,19,  2495.00,  449.10,  2944.10,TRUE, '2025-04-04','2025-03-05'),
  (45,20, 22000.00, 3960.00, 25960.00,TRUE, '2025-04-21','2025-03-22'),
  (46, 5, 52000.00, 9360.00, 61360.00,TRUE, '2025-05-05','2025-04-05'),
  (47, 2, 45000.00, 8100.00, 53100.00,TRUE, '2025-05-18','2025-04-18'),
  (48,10, 35000.00, 6300.00, 41300.00,FALSE,'2025-06-01','2025-05-02'),
  (49, 1, 52000.00, 9360.00, 61360.00,TRUE, '2025-06-14','2025-05-15'),
  (50, 3, 45000.00, 8100.00, 53100.00,TRUE, '2025-06-27','2025-05-28');

-- ── Support Tickets (20 rows) ────────────────────────────────
INSERT INTO support_tickets (customer_id,assigned_to,subject,priority,status,created_at,resolved_at) VALUES
  ( 1,11,'DataLens login failure after update',        'high',  'resolved','2025-01-05','2025-01-06'),
  ( 2, 7,'CRM sync delay with Salesforce',             'medium','resolved','2025-01-12','2025-01-15'),
  ( 3,11,'SecureID token expiry too short',            'low',   'resolved','2025-02-01','2025-02-04'),
  ( 5,11,'NeuralChat rate limit exceeded',             'high',  'open',    '2025-02-20',NULL),
  ( 6, 7,'Billing discrepancy on invoice #6',          'medium','resolved','2025-03-01','2025-03-03'),
  ( 7,11,'CSV export corrupted in ReportMagic',        'low',   'open',    '2025-03-15',NULL),
  ( 4, 7,'InsightBoard dashboard timeout',             'high',  'resolved','2025-03-20','2025-03-21'),
  (10,11,'DataLens API key rotation needed',           'medium','resolved','2025-04-02','2025-04-03'),
  ( 9, 7,'Compliance Shield false positive alerts',    'high',  'open',    '2025-04-10',NULL),
  ( 8,11,'FlowSync webhook timeout',                   'medium','open',    '2025-04-18',NULL),
  (11,25,'AIWorkflow Suite onboarding issue',          'medium','resolved','2025-01-20','2025-01-22'),
  (12,32,'InsightBoard slow queries',                  'low',   'open',    '2025-02-05',NULL),
  (13,11,'DataLens Enterprise SSO config',             'high',  'resolved','2025-02-15','2025-02-16'),
  (14, 7,'FlowSync missing events',                    'medium','resolved','2025-03-08','2025-03-10'),
  (15,11,'CloudVault storage limit hit',               'high',  'open',    '2025-03-25',NULL),
  (16,25,'AIWorkflow Suite billing error',             'medium','resolved','2025-04-01','2025-04-02'),
  (17,32,'ReportMagic PDF export blank',               'low',   'open',    '2025-04-12',NULL),
  (18, 7,'NeuralChat AI hallucination report',         'high',  'open',    '2025-04-22',NULL),
  (19,11,'DataLens Starter upgrade request',           'low',   'resolved','2025-05-01','2025-05-02'),
  (20,25,'GlobalMart CRM integration failure',         'high',  'open',    '2025-05-10',NULL);

