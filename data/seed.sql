-- ============================================================
-- Seed data for the healthcare support chatbot demo.
-- Three client hospitals so cross-client scoping can be tested.
-- ============================================================

-- Users -----------------------------------------------------
INSERT INTO users (client_id, email, org_name, contact_name, phone) VALUES
 ('CLI-1001', 'admin@stmary-hospital.org',   'St. Mary Hospital',        'Dr. Anita Rao',   '+1-202-555-0101'),
 ('CLI-1002', 'ops@greenvalley-clinic.com',  'Green Valley Clinic',      'Mr. John Fields', '+1-202-555-0102'),
 ('CLI-1003', 'proc@lakeside-medical.org',   'Lakeside Medical Center',  'Ms. Lisa Chen',   '+1-202-555-0103');

-- Equipment catalogue --------------------------------------
INSERT INTO equipment (equipment_id, model_name, category, manufacturer, manual_doc, list_price_usd) VALUES
 ('EQ-MRI-15T',  'MagnaScan 1.5T MRI',        'MRI',        'MediCorp', 'mri_scanner_manual.md',        1200000),
 ('EQ-CT-64',    'ClariCT 64-Slice Scanner',  'CT',         'MediCorp', 'ct_scanner_manual.md',          650000),
 ('EQ-US-PRO',   'SonoPro Ultrasound',        'Ultrasound', 'MediCorp', 'general_support_faq.md',         85000),
 ('EQ-MON-VS',   'VitalGuard Patient Monitor','Monitor',    'MediCorp', 'general_support_faq.md',         12000);

-- Orders ----------------------------------------------------
INSERT INTO orders (order_id, client_id, equipment_id, quantity, order_date, status, est_delivery, tracking_no, notes) VALUES
 ('ORD-4401', 'CLI-1001', 'EQ-MRI-15T', 1, '2026-06-15', 'Delivered',  '2026-07-20', 'TRK-88123', 'Installed successfully'),
 ('ORD-4402', 'CLI-1001', 'EQ-CT-64',   1, '2026-07-10', 'In Transit', '2026-08-14', 'TRK-88231', 'Customs cleared'),
 ('ORD-4403', 'CLI-1002', 'EQ-US-PRO',  2, '2026-07-25', 'Processing', '2026-08-30', NULL,        'Awaiting stock'),
 ('ORD-4404', 'CLI-1002', 'EQ-MON-VS',  5, '2026-07-28', 'Delayed',    '2026-08-22', 'TRK-88345', 'Shipment delayed by weather'),
 ('ORD-4405', 'CLI-1003', 'EQ-CT-64',   1, '2026-06-30', 'Shipped',    '2026-08-12', 'TRK-88410', NULL);

-- Warranty / AMC -------------------------------------------
INSERT INTO warranty_amc (contract_id, client_id, order_id, equipment_id, warranty_start, warranty_end, amc_plan, amc_status, amc_end) VALUES
 ('WAR-9001', 'CLI-1001', 'ORD-4401', 'EQ-MRI-15T', '2026-07-20', '2028-07-19', 'Premium',   'Active',     '2027-07-19'),
 ('WAR-9002', 'CLI-1001', 'ORD-4402', 'EQ-CT-64',   NULL,         NULL,         'None',      'NotEnrolled', NULL),
 ('WAR-9003', 'CLI-1002', 'ORD-4404', 'EQ-MON-VS',  '2026-08-22', '2027-08-21', 'Basic',     'Active',     '2026-11-21'),
 ('WAR-9004', 'CLI-1003', 'ORD-4405', 'EQ-CT-64',   '2026-08-12', '2028-08-11', 'Standard',  'Active',     '2027-08-11');

-- Complaints -----------------------------------------------
INSERT INTO complaints (ticket_id, client_id, equipment_id, subject, priority, status, created_at, updated_at, assigned_team) VALUES
 ('TIC-7001', 'CLI-1001', 'EQ-MRI-15T', 'Cooling unit making noise',       'High',     'In Progress', '2026-07-30', '2026-08-02', 'Field Service'),
 ('TIC-7002', 'CLI-1002', 'EQ-MON-VS',  'Two monitors not powering on',    'Critical', 'Escalated',   '2026-08-01', '2026-08-05', 'L2 Support'),
 ('TIC-7003', 'CLI-1003', 'EQ-CT-64',   'Calibration warning on startup',  'Medium',   'Open',        '2026-08-04', NULL,         'Field Service');

-- Invoices --------------------------------------------------
INSERT INTO invoices (invoice_id, client_id, order_id, amount_usd, issued_date, due_date, status, pdf_link) VALUES
 ('INV-3001', 'CLI-1001', 'ORD-4401', 1200000, '2026-07-21', '2026-08-21', 'Paid',    'https://portal.medicorp.example/inv/INV-3001.pdf'),
 ('INV-3002', 'CLI-1001', 'ORD-4402', 650000,  '2026-07-12', '2026-08-12', 'Overdue', 'https://portal.medicorp.example/inv/INV-3002.pdf'),
 ('INV-3003', 'CLI-1002', 'ORD-4404', 60000,   '2026-07-29', '2026-08-29', 'Unpaid',  'https://portal.medicorp.example/inv/INV-3003.pdf'),
 ('INV-3004', 'CLI-1003', 'ORD-4405', 650000,  '2026-07-01', '2026-08-01', 'Paid',    'https://portal.medicorp.example/inv/INV-3004.pdf');

-- Spare parts (shared catalogue, not client-scoped) --------
INSERT INTO spare_parts (part_id, part_name, compatible_with, in_stock, unit_price_usd, lead_time_days) VALUES
 ('SP-201', 'MRI Cooling Pump',        'EQ-MRI-15T', 4,  8500, 7),
 ('SP-202', 'CT X-ray Tube',           'EQ-CT-64',   0,  45000, 21),
 ('SP-203', 'Ultrasound Probe L12-5',  'EQ-US-PRO',  12, 3200, 5),
 ('SP-204', 'Monitor Power Board',     'EQ-MON-VS',  25, 180,  3),
 ('SP-205', 'ECG Cable 5-Lead',        'EQ-MON-VS',  60, 45,   2);
