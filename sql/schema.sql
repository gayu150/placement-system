-- ==============================================================
-- Recruitment & Placement Management System
-- Database Schema (MySQL Compatible)
-- ==============================================================

CREATE DATABASE IF NOT EXISTS `placement_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `placement_db`;

-- Drop existing tables in reverse dependency order if recreating
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `activity_logs`;
DROP TABLE IF EXISTS `placements`;
DROP TABLE IF EXISTS `offers`;
DROP TABLE IF EXISTS `interview_feedback`;
DROP TABLE IF EXISTS `interview_rounds`;
DROP TABLE IF EXISTS `application_history`;
DROP TABLE IF EXISTS `applications`;
DROP TABLE IF EXISTS `job_skills`;
DROP TABLE IF EXISTS `jobs`;
DROP TABLE IF EXISTS `companies`;
DROP TABLE IF EXISTS `candidate_skills`;
DROP TABLE IF EXISTS `candidates`;
DROP TABLE IF EXISTS `skills`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `roles`;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Roles table
CREATE TABLE `roles` (
    `role_id` INT AUTO_INCREMENT PRIMARY KEY,
    `role_name` VARCHAR(50) NOT NULL UNIQUE,
    `description` VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Users table (Admin, Recruiter, Placement Officer)
CREATE TABLE `users` (
    `user_id` INT AUTO_INCREMENT PRIMARY KEY,
    `role_id` INT NOT NULL,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_users_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`role_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Skills master table
CREATE TABLE `skills` (
    `skill_id` INT AUTO_INCREMENT PRIMARY KEY,
    `skill_name` VARCHAR(100) NOT NULL UNIQUE,
    `category` VARCHAR(50) NOT NULL DEFAULT 'General'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Candidates table
CREATE TABLE `candidates` (
    `candidate_id` INT AUTO_INCREMENT PRIMARY KEY,
    `candidate_code` VARCHAR(30) NOT NULL UNIQUE,
    `first_name` VARCHAR(50) NOT NULL,
    `last_name` VARCHAR(50) NOT NULL,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `mobile` VARCHAR(20) NOT NULL UNIQUE,
    `date_of_birth` DATE NULL,
    `gender` VARCHAR(20) NULL,
    `qualification` VARCHAR(50) NOT NULL,
    `college` VARCHAR(150) NOT NULL,
    `university` VARCHAR(150) NOT NULL,
    `passing_year` INT NOT NULL,
    `percentage` DECIMAL(5,2) NOT NULL,
    `cgpa` DECIMAL(4,2) NULL,
    `backlog_count` INT NOT NULL DEFAULT 0,
    `primary_technology` VARCHAR(100) NOT NULL,
    `skill_proficiency` VARCHAR(50) NOT NULL DEFAULT 'Intermediate',
    `experience_years` DECIMAL(4,2) NOT NULL DEFAULT 0.00,
    `current_location` VARCHAR(100) NOT NULL,
    `preferred_location` VARCHAR(100) NOT NULL,
    `profile_status` VARCHAR(20) NOT NULL DEFAULT 'Active',
    `placement_status` VARCHAR(30) NOT NULL DEFAULT 'Unplaced',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `chk_candidate_percentage` CHECK (`percentage` >= 0.00 AND `percentage` <= 100.00),
    CONSTRAINT `chk_candidate_backlog` CHECK (`backlog_count` >= 0),
    CONSTRAINT `chk_candidate_profile_status` CHECK (`profile_status` IN ('Active', 'Inactive')),
    CONSTRAINT `chk_candidate_placement_status` CHECK (`placement_status` IN ('Unplaced', 'In Process', 'Placed', 'Opted Out'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Candidate Skills mapping
CREATE TABLE `candidate_skills` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `candidate_id` INT NOT NULL,
    `skill_id` INT NOT NULL,
    `proficiency_level` VARCHAR(50) NOT NULL DEFAULT 'Intermediate',
    CONSTRAINT `fk_cand_skills_candidate` FOREIGN KEY (`candidate_id`) REFERENCES `candidates` (`candidate_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cand_skills_skill` FOREIGN KEY (`skill_id`) REFERENCES `skills` (`skill_id`) ON DELETE RESTRICT,
    CONSTRAINT `uq_candidate_skill` UNIQUE (`candidate_id`, `skill_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Companies table
CREATE TABLE `companies` (
    `company_id` INT AUTO_INCREMENT PRIMARY KEY,
    `company_code` VARCHAR(30) NOT NULL UNIQUE,
    `company_name` VARCHAR(150) NOT NULL,
    `industry` VARCHAR(100) NOT NULL,
    `website` VARCHAR(255) NULL,
    `location` VARCHAR(100) NOT NULL,
    `company_type` VARCHAR(50) NOT NULL DEFAULT 'Service',
    `hr_name` VARCHAR(100) NOT NULL,
    `hr_email` VARCHAR(100) NOT NULL,
    `hr_phone` VARCHAR(20) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'Active',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `chk_company_status` CHECK (`status` IN ('Active', 'Inactive'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Jobs table
CREATE TABLE `jobs` (
    `job_id` INT AUTO_INCREMENT PRIMARY KEY,
    `job_code` VARCHAR(30) NOT NULL UNIQUE,
    `company_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `employment_type` VARCHAR(50) NOT NULL DEFAULT 'Full-time',
    `location` VARCHAR(100) NOT NULL,
    `openings` INT NOT NULL,
    `min_package` DECIMAL(10,2) NOT NULL,
    `max_package` DECIMAL(10,2) NOT NULL,
    `qualification_req` VARCHAR(100) NOT NULL,
    `min_percentage` DECIMAL(5,2) NOT NULL DEFAULT 60.00,
    `min_passing_year` INT NOT NULL,
    `max_passing_year` INT NOT NULL,
    `max_backlogs` INT NOT NULL DEFAULT 0,
    `experience_req` DECIMAL(4,2) NOT NULL DEFAULT 0.00,
    `posted_date` DATE NOT NULL,
    `deadline` DATE NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'Open',
    `created_by` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_jobs_company` FOREIGN KEY (`company_id`) REFERENCES `companies` (`company_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_jobs_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
    CONSTRAINT `chk_job_openings` CHECK (`openings` > 0),
    CONSTRAINT `chk_job_package` CHECK (`min_package` <= `max_package`),
    CONSTRAINT `chk_job_deadline` CHECK (`deadline` >= `posted_date`),
    CONSTRAINT `chk_job_status` CHECK (`status` IN ('Draft', 'Open', 'Closed', 'Cancelled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Job Skills requirement mapping
CREATE TABLE `job_skills` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `job_id` INT NOT NULL,
    `skill_id` INT NOT NULL,
    `is_mandatory` TINYINT(1) NOT NULL DEFAULT 1,
    `min_proficiency` VARCHAR(50) NOT NULL DEFAULT 'Intermediate',
    CONSTRAINT `fk_job_skills_job` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`job_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_job_skills_skill` FOREIGN KEY (`skill_id`) REFERENCES `skills` (`skill_id`) ON DELETE RESTRICT,
    CONSTRAINT `uq_job_skill` UNIQUE (`job_id`, `skill_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Applications table
CREATE TABLE `applications` (
    `application_id` INT AUTO_INCREMENT PRIMARY KEY,
    `application_code` VARCHAR(30) NOT NULL UNIQUE,
    `candidate_id` INT NOT NULL,
    `job_id` INT NOT NULL,
    `applied_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `current_stage` VARCHAR(40) NOT NULL DEFAULT 'APPLIED',
    `eligibility_status` VARCHAR(20) NOT NULL,
    `eligibility_remarks` TEXT NULL,
    `is_override` TINYINT(1) NOT NULL DEFAULT 0,
    `override_reason` TEXT NULL,
    `override_by` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_app_candidate` FOREIGN KEY (`candidate_id`) REFERENCES `candidates` (`candidate_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_app_job` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`job_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_app_override_user` FOREIGN KEY (`override_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
    CONSTRAINT `uq_cand_job_application` UNIQUE (`candidate_id`, `job_id`),
    CONSTRAINT `chk_app_stage` CHECK (`current_stage` IN (
        'APPLIED', 'ELIGIBILITY_VERIFIED', 'SHORTLISTED',
        'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'SELECTED',
        'OFFERED', 'JOINED', 'REJECTED', 'WITHDRAWN'
    )),
    CONSTRAINT `chk_app_eligibility` CHECK (`eligibility_status` IN ('ELIGIBLE', 'NOT_ELIGIBLE'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. Application History table
CREATE TABLE `application_history` (
    `history_id` INT AUTO_INCREMENT PRIMARY KEY,
    `application_id` INT NOT NULL,
    `old_stage` VARCHAR(40) NOT NULL,
    `new_stage` VARCHAR(40) NOT NULL,
    `remarks` TEXT NULL,
    `changed_by` INT NULL,
    `changed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_history_application` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_history_user` FOREIGN KEY (`changed_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. Interview Rounds table
CREATE TABLE `interview_rounds` (
    `interview_id` INT AUTO_INCREMENT PRIMARY KEY,
    `application_id` INT NOT NULL,
    `round_number` INT NOT NULL,
    `round_name` VARCHAR(50) NOT NULL,
    `scheduled_date` DATE NOT NULL,
    `scheduled_time` TIME NOT NULL,
    `interview_mode` VARCHAR(30) NOT NULL DEFAULT 'Online',
    `interviewer_name` VARCHAR(100) NOT NULL,
    `meeting_link_or_venue` VARCHAR(255) NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'SCHEDULED',
    `scheduled_by` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_rounds_application` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_rounds_user` FOREIGN KEY (`scheduled_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
    CONSTRAINT `uq_application_round` UNIQUE (`application_id`, `round_number`),
    CONSTRAINT `chk_round_status` CHECK (`status` IN ('SCHEDULED', 'COMPLETED', 'CANCELLED', 'NO_SHOW', 'RESCHEDULED')),
    CONSTRAINT `chk_round_mode` CHECK (`interview_mode` IN ('Online', 'In-person'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 12. Interview Feedback table
CREATE TABLE `interview_feedback` (
    `feedback_id` INT AUTO_INCREMENT PRIMARY KEY,
    `interview_id` INT NOT NULL UNIQUE,
    `technical_rating` INT NOT NULL,
    `communication_rating` INT NOT NULL,
    `problem_solving_rating` INT NOT NULL,
    `overall_rating` INT NOT NULL,
    `recommendation` VARCHAR(30) NOT NULL,
    `remarks` TEXT NOT NULL,
    `submitted_by` INT NULL,
    `submitted_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_feedback_interview` FOREIGN KEY (`interview_id`) REFERENCES `interview_rounds` (`interview_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_feedback_user` FOREIGN KEY (`submitted_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
    CONSTRAINT `chk_tech_rating` CHECK (`technical_rating` BETWEEN 1 AND 5),
    CONSTRAINT `chk_comm_rating` CHECK (`communication_rating` BETWEEN 1 AND 5),
    CONSTRAINT `chk_ps_rating` CHECK (`problem_solving_rating` BETWEEN 1 AND 5),
    CONSTRAINT `chk_overall_rating` CHECK (`overall_rating` BETWEEN 1 AND 5),
    CONSTRAINT `chk_recommendation` CHECK (`recommendation` IN ('NEXT_ROUND', 'SELECTED', 'REJECTED', 'ON_HOLD'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 13. Offers table
CREATE TABLE `offers` (
    `offer_id` INT AUTO_INCREMENT PRIMARY KEY,
    `offer_code` VARCHAR(30) NOT NULL UNIQUE,
    `application_id` INT NOT NULL UNIQUE,
    `candidate_id` INT NOT NULL,
    `company_id` INT NOT NULL,
    `job_id` INT NOT NULL,
    `designation` VARCHAR(100) NOT NULL,
    `package_lpa` DECIMAL(10,2) NOT NULL,
    `offer_date` DATE NOT NULL,
    `expected_joining_date` DATE NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'OFFERED',
    `remarks` TEXT NULL,
    `created_by` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_offers_application` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_offers_candidate` FOREIGN KEY (`candidate_id`) REFERENCES `candidates` (`candidate_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_offers_company` FOREIGN KEY (`company_id`) REFERENCES `companies` (`company_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_offers_job` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`job_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_offers_user` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
    CONSTRAINT `chk_offer_status` CHECK (`status` IN ('OFFERED', 'ACCEPTED', 'REJECTED', 'EXPIRED', 'WITHDRAWN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 14. Placements table
CREATE TABLE `placements` (
    `placement_id` INT AUTO_INCREMENT PRIMARY KEY,
    `placement_code` VARCHAR(30) NOT NULL UNIQUE,
    `offer_id` INT NOT NULL UNIQUE,
    `candidate_id` INT NOT NULL,
    `company_id` INT NOT NULL,
    `job_id` INT NOT NULL,
    `designation` VARCHAR(100) NOT NULL,
    `final_package_lpa` DECIMAL(10,2) NOT NULL,
    `expected_joining_date` DATE NOT NULL,
    `actual_joining_date` DATE NULL,
    `joining_status` VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    `remarks` TEXT NULL,
    `recorded_by` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_placements_offer` FOREIGN KEY (`offer_id`) REFERENCES `offers` (`offer_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_placements_candidate` FOREIGN KEY (`candidate_id`) REFERENCES `candidates` (`candidate_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_placements_company` FOREIGN KEY (`company_id`) REFERENCES `companies` (`company_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_placements_job` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`job_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_placements_user` FOREIGN KEY (`recorded_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
    CONSTRAINT `chk_joining_status` CHECK (`joining_status` IN ('PENDING', 'JOINED', 'NOT_JOINED', 'DEFERRED', 'NO_SHOW'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 15. Activity Logs table
CREATE TABLE `activity_logs` (
    `log_id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `user_name` VARCHAR(100) NULL,
    `module` VARCHAR(50) NOT NULL,
    `action` VARCHAR(50) NOT NULL,
    `record_id` VARCHAR(50) NULL,
    `description` TEXT NOT NULL,
    `ip_address` VARCHAR(50) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Indexes for performance
CREATE INDEX `idx_cand_tech` ON `candidates` (`primary_technology`);
CREATE INDEX `idx_cand_status` ON `candidates` (`profile_status`, `placement_status`);
CREATE INDEX `idx_jobs_company` ON `jobs` (`company_id`, `status`);
CREATE INDEX `idx_apps_candidate` ON `applications` (`candidate_id`);
CREATE INDEX `idx_apps_job` ON `applications` (`job_id`);
CREATE INDEX `idx_apps_stage` ON `applications` (`current_stage`);
CREATE INDEX `idx_rounds_date` ON `interview_rounds` (`scheduled_date`, `status`);
CREATE INDEX `idx_logs_module` ON `activity_logs` (`module`, `created_at`);

