import 'package:flutter_test/flutter_test.dart';
import 'package:kuru_app/models/agent_workflow.dart';
import 'package:kuru_app/models/job_application.dart';
import 'package:kuru_app/models/job_listing.dart';
import 'package:kuru_app/models/notification_item.dart';
import 'package:kuru_app/models/reminder_item.dart';
import 'package:kuru_app/models/resume.dart';
import 'package:kuru_app/models/skill_gap.dart';
import 'package:kuru_app/models/user_profile.dart';

void main() {
  group('StudentProfile Model Tests', () {
    test('StudentProfile parses from JSON and serializes back', () {
      final json = {
        'id': 12,
        'firebase_uid': 'test_uid_456',
        'full_name': 'Aarav Sharma',
        'email': 'aarav@example.com',
        'headline': 'Final Year CS Student',
        'education_level': 'Bachelor of Technology',
        'field_of_study': 'Computer Science',
        'institution_name': 'IIT Bombay',
        'graduation_year': 2026,
        'target_roles': ['Backend Engineer', 'DevOps Engineer'],
        'interests': ['Distributed Systems', 'Cloud'],
        'preferred_locations': ['Bangalore', 'Remote'],
        'preferred_work_modes': ['remote', 'hybrid'],
      };

      final profile = StudentProfile.fromJson(json);
      expect(profile.id, 12);
      expect(profile.firebaseUid, 'test_uid_456');
      expect(profile.fullName, 'Aarav Sharma');
      expect(profile.targetRoles, contains('Backend Engineer'));
      expect(profile.preferredLocations, contains('Bangalore'));

      final serialized = profile.toJson();
      expect(serialized['firebase_uid'], 'test_uid_456');
      expect(serialized['full_name'], 'Aarav Sharma');
    });
  });

  group('JobListing Model Tests', () {
    test('JobListing correctly parses match scores and skill lists', () {
      final json = {
        'id': 'job_ind_789',
        'title': 'Junior Python Backend Developer',
        'company': 'Razorpay',
        'location': 'Bangalore, India',
        'work_mode': 'hybrid',
        'job_type': 'full-time',
        'source_platform': 'Naukri Verified',
        'source_url': 'https://naukri.com/job/789',
        'required_skills': ['Python', 'FastAPI', 'PostgreSQL', 'Docker'],
        'matched_skills': ['Python', 'FastAPI'],
        'missing_skills': ['Docker'],
        'match_score': 82.5,
        'match_reasons': ['Matched 2 core skills', 'Target role matches Backend Engineer'],
        'is_saved': true,
      };

      final job = JobListing.fromJson(json);
      expect(job.id, 'job_ind_789');
      expect(job.company, 'Razorpay');
      expect(job.matchScore, 82.5);
      expect(job.matchedSkills.length, 2);
      expect(job.missingSkills, contains('Docker'));
      expect(job.isSaved, isTrue);

      final toggled = job.copyWith(isSaved: false);
      expect(toggled.isSaved, isFalse);
    });
  });

  group('Skill & Simulation Models', () {
    test('PrioritizedSkillGap and WhatIfSimulation parse accurately', () {
      final gapJson = {
        'skill_name': 'Docker',
        'category': 'DevOps',
        'demand_frequency': 18,
        'urgency': 'high',
        'rationale': 'Required in 18 target job listings in India.',
      };

      final gap = PrioritizedSkillGap.fromJson(gapJson);
      expect(gap.skillName, 'Docker');
      expect(gap.demandFrequency, 18);
      expect(gap.urgency, 'high');

      final simJson = {
        'target_role': 'Backend Engineer',
        'baseline_score': 64.0,
        'projected_score': 85.0,
        'score_lift': 21.0,
        'newly_eligible_jobs_count': 7,
        'simulated_skills': ['Docker', 'Redis'],
      };

      final sim = WhatIfSimulationResult.fromJson(simJson);
      expect(sim.baselineScore, 64.0);
      expect(sim.projectedScore, 85.0);
      expect(sim.scoreLift, 21.0);
      expect(sim.newlyEligibleJobsCount, 7);
    });
  });

  group('Agent Workflow Models', () {
    test('AgentApprovalRequest parses approval payload', () {
      final approvalJson = {
        'id': 42,
        'action_type': 'submit_application',
        'status': 'pending',
        'action_description': 'Submit tailored resume to Razorpay for Backend Role',
        'payload': {
          'job_id': 'job_ind_789',
          'resume_length': 1200,
        },
      };

      final req = AgentApprovalRequest.fromJson(approvalJson);
      expect(req.id, 42);
      expect(req.actionType, 'submit_application');
      expect(req.status, 'pending');
      expect(req.payload['job_id'], 'job_ind_789');
    });
  });

  group('Resume & Application Tracking Models', () {
    test('ResumeModel parses complex ATS resume with verified citations and assessments', () {
      final resumeJson = {
        'id': 'res_123',
        'firebase_uid': 'test_user_789',
        'title': 'ATS Tailored Resume - Razorpay',
        'target_role': 'Backend Engineer',
        'job_id': 'job_ind_789',
        'is_primary': true,
        'contact_info': {
          'name': 'Aarav Sharma',
          'email': 'aarav@example.com',
          'phone': '+91-9876543210',
          'github': 'github.com/aaravsharma',
          'location': 'Bangalore, India',
        },
        'summary': 'Evidence-grounded Backend Engineer with practical proficiency in Python and FastAPI.',
        'skills_by_category': {
          'Backend': [
            {
              'name': 'Python',
              'category': 'Backend',
              'evidence_paths': ['app/main.py', 'services/matcher.py'],
              'proficiency_level': 'verified',
              'assessment_score': 95.0,
            },
            {
              'name': 'FastAPI',
              'category': 'Backend',
              'evidence_paths': ['app/api/v1/router.py'],
              'proficiency_level': 'verified',
              'assessment_score': 90.0,
            },
          ],
        },
        'experience': [],
        'projects': [
          {
            'title': 'Kuru Backend',
            'repo_name': 'kuru_backend',
            'summary': 'Microservices backend using FastAPI and PostgreSQL.',
            'bullets': [
              'Architected ATS resume generation engine with zero hallucination guarantee.',
            ],
            'technologies': ['Python', 'FastAPI', 'PostgreSQL'],
            'github_url': 'https://github.com/aaravsharma/kuru_backend',
          },
        ],
        'education': [
          {
            'institution': 'IIT Bombay',
            'degree': 'B.Tech',
            'graduation_year': 2026,
            'field_of_study': 'Computer Science',
          },
        ],
        'practical_assessments': [
          {
            'skill_name': 'Python',
            'score': 95.0,
            'level': 'intermediate',
            'passed': true,
            'verification_date': '2026-10-16',
          },
        ],
        'tailoring_metadata': {
          'target_role': 'Backend Engineer',
          'target_company': 'Razorpay',
          'job_id': 'job_ind_789',
          'matched_skills': ['Python', 'FastAPI'],
          'missing_skills': ['Docker'],
          'evidence_citations': {
            'Python': ['app/main.py'],
            'FastAPI': ['app/api/v1/router.py'],
          },
          'anti_hallucination_verified': true,
        },
      };

      final resume = ResumeModel.fromJson(resumeJson);
      expect(resume.id, 'res_123');
      expect(resume.contactInfo.name, 'Aarav Sharma');
      expect(resume.skillsByCategory['Backend']?.length, 2);
      expect(resume.practicalAssessments.first.passed, isTrue);
      expect(resume.tailoringMetadata?.antiHallucinationVerified, isTrue);
      expect(resume.tailoringMetadata?.evidenceCitations['Python'], contains('app/main.py'));

      final serialized = resume.toJson();
      expect(serialized['id'], 'res_123');
      expect(serialized['title'], 'ATS Tailored Resume - Razorpay');
    });

    test('JobApplication and ApplicationPrepareResult parse lifecycle and stage approval', () {
      final appJson = {
        'id': 'app_rec_001',
        'firebase_uid': 'test_user_789',
        'job_id': 'job_ind_789',
        'status': 'applied',
        'notes': 'Submitted following approval.',
        'deadline': '2026-11-01',
        'submitted_at': '2026-10-16T18:00:00Z',
        'resume_id': 'res_123',
        'application_packet': {
          'match_score': 88.0,
          'requires_human_approval': true,
          'auto_submission_prevented': true,
        },
      };

      final app = JobApplication.fromJson(appJson);
      expect(app.id, 'app_rec_001');
      expect(app.status, 'applied');
      expect(app.applicationPacket['auto_submission_prevented'], isTrue);

      final prepJson = {
        'job_id': 'job_ind_789',
        'approval_request_id': 105,
        'status': 'pending_approval',
        'application_packet': {
          'job_title': 'Backend Developer',
        },
      };

      final prep = ApplicationPrepareResult.fromJson(prepJson);
      expect(prep.jobId, 'job_ind_789');
      expect(prep.approvalRequestId, 105);
      expect(prep.status, 'pending_approval');
    });
  });

  group('Notification & Reminder Models', () {
    test('NotificationItem parses JSON, serializes back, and supports copyWith', () {
      final notifJson = {
        'id': 'notif_001',
        'firebase_uid': 'user_123',
        'title': 'Interview Scheduled',
        'message': 'Round 1 technical discussion with Razorpay.',
        'notification_type': 'interview',
        'entity_type': 'application',
        'entity_id': 'job_789',
        'is_read': false,
        'data': {'job_id': 'job_789'},
        'created_at': '2026-10-17T03:00:00Z',
        'updated_at': '2026-10-17T03:00:00Z',
      };

      final item = NotificationItem.fromJson(notifJson);
      expect(item.id, 'notif_001');
      expect(item.title, 'Interview Scheduled');
      expect(item.notificationType, 'interview');
      expect(item.isRead, isFalse);

      final readCopy = item.copyWith(isRead: true);
      expect(readCopy.isRead, isTrue);

      final jsonOut = item.toJson();
      expect(jsonOut['id'], 'notif_001');
      expect(jsonOut['notification_type'], 'interview');
    });

    test('ReminderItem correctly parses JSON and computes overdue status', () {
      final pastDue = DateTime.now().subtract(const Duration(hours: 3)).toUtc().toIso8601String();
      final reminderJson = {
        'id': 'rem_001',
        'firebase_uid': 'user_123',
        'job_id': 'job_789',
        'title': 'Submit take-home assignment',
        'description': 'Follow up with recruiter on GitHub repo link',
        'due_date': pastDue,
        'reminder_type': 'deadline',
        'is_completed': false,
        'is_dismissed': false,
        'created_at': '2026-10-16T12:00:00Z',
        'updated_at': '2026-10-16T12:00:00Z',
      };

      final rem = ReminderItem.fromJson(reminderJson);
      expect(rem.id, 'rem_001');
      expect(rem.title, 'Submit take-home assignment');
      expect(rem.reminderType, 'deadline');
      expect(rem.isCompleted, isFalse);
      expect(rem.isOverdue, isTrue);

      final completed = rem.copyWith(isCompleted: true, isOverdue: false);
      expect(completed.isCompleted, isTrue);
      expect(completed.isOverdue, isFalse);
    });
  });
}
