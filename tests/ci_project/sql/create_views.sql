CREATE OR REPLACE VIEW topemployees AS
  SELECT * FROM employees WHERE salary > 2000;