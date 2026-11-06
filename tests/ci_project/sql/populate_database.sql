INSERT INTO departments (departmentId, name, city)
    VALUES
	(1, 'Arte', 'Cádiz'),
	(2, 'Historia', NULL),
	(3, 'Informática', 'Sevilla');

INSERT INTO employees (employeeId, email, password, departmentId, bossId, firstName, lastName, salary, position, isActive)
    VALUES
	(1, "perianez@company.com", "$argon2id$v=19$m=65536,t=3,p=4$fICiwIj6zZ7m1q06IeByBA$CytyUF9eTgHtiiU3Mlp2STmIfAucziha4Rqno1Buino", 1, NULL, 'Pedro', 'Periáñez', 2300, 'Manager', TRUE),
	(2, "jimenez@company.com", "$argon2id$v=19$m=65536,t=3,p=4$aYgrBf5hK35Q0Z6JsMgM3Q$t+nWAs1UEtyojLpEG2U5kD1Qkva32NylbQSrQonYsQY", 1, 1, 'José', 'Jiménez', 2500, 'CEO', TRUE),
	(3, "lacalle@company.com", "$argon2id$v=19$m=65536,t=3,p=4$r1M/mdK17LKdCyqYY3Ld6w$6vWNkUeK5AjwONmlxgIFbNA8L/Um5W7jKfa4uiaMX1I", 2, 2, 'Lola', 'Lacalle', 2300, 'Manager', TRUE),
	(4, "linares@company.com", "$argon2id$v=19$m=65536,t=3,p=4$vHbqI4OJ3D+RRIEyZF5rxQ$g4WVgAzf4u6q3OKziAqfeaV+VDWv1OBK3y2pBKvCIa4", 1, 2, 'Luis', 'Linares', 1300, 'Programmer', TRUE),
	(5, "alvarez@company.com", "$argon2id$v=19$m=65536,t=3,p=4$t5/YhWBr/WJ9cBnVaiRHVg$R0oGgDfxEd9S1VddTSR4NDvcSbluc64wlrwZ3xMRcx8", 1, 3, 'Ana', 'Álvarez', 1300, NULL, TRUE);
-- The passwords are the email usernames (what goes before the @), as argon2 hashes
