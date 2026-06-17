class PosTransaction {
  final int id;
  final int customerId;
  final String type;
  final double amount;
  final String note;
  final DateTime dt;

  PosTransaction({
    required this.id,
    required this.customerId,
    required this.type,
    required this.amount,
    required this.note,
    required this.dt,
  });

  factory PosTransaction.fromMap(Map<String, dynamic> m) => PosTransaction(
        id: m['id'] as int,
        customerId: m['customer_id'] as int,
        type: m['type'] as String,
        amount: (m['amount'] as num).toDouble(),
        note: m['note'] as String? ?? '',
        dt: DateTime.parse((m['dt'] as String).replaceAll(' ', 'T')),
      );
}
