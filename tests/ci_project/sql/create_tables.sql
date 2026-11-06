DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
  departmentId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(128) DEFAULT NULL,
  city VARCHAR(64) DEFAULT NULL,
  UNIQUE (name, city)
);

CREATE TABLE employees (
  employeeId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(256) UNIQUE NOT NULL,
  password VARCHAR(512) NOT NULL,
  departmentId INT DEFAULT NULL,
  bossId INT DEFAULT NULL,
  firstName VARCHAR(256) NOT NULL,
  lastName VARCHAR(256) NOT NULL,
  salary DOUBLE DEFAULT 2000,
  position VARCHAR(256),
  isActive BOOLEAN NOT NULL,
  FOREIGN KEY (departmentId) REFERENCES departments (departmentId) ON DELETE SET NULL,
  FOREIGN KEY (bossId) REFERENCES employees (employeeId),
  CONSTRAINT validSalary CHECK (salary > 0)
);
