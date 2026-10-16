class CareerNote {
  final String id;
  final String uid;
  final String title;
  final String content;
  final List<String> tags;
  final DateTime createdAt;
  final DateTime updatedAt;

  CareerNote({
    required this.id,
    required this.uid,
    required this.title,
    required this.content,
    this.tags = const [],
    required this.createdAt,
    required this.updatedAt,
  });

  factory CareerNote.fromJson(Map<String, dynamic> json, [String? docId]) {
    DateTime parseDate(dynamic val) {
      if (val is DateTime) return val;
      if (val is String) return DateTime.tryParse(val) ?? DateTime.now();
      return DateTime.now();
    }

    return CareerNote(
      id: docId ?? json['id']?.toString() ?? '',
      uid: json['uid']?.toString() ?? json['firebase_uid']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      content: json['content']?.toString() ?? '',
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      createdAt: parseDate(json['created_at']),
      updatedAt: parseDate(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'uid': uid,
      'title': title,
      'content': content,
      'tags': tags,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}
