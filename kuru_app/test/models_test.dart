import 'package:flutter_test/flutter_test.dart';
import 'package:kuru_app/models/agent_workflow.dart';
import 'package:kuru_app/models/job_listing.dart';
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
}
