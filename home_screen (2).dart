class Customer {
  final int id;
  final String name;

  Customer({required this.id, required this.name});

  factory Customer.fromMap(Map<String, dynamic> m) =>
      Customer(id: m['id'] as int, name: m['name'] as String);
}
