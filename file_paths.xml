import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/customer.dart';
import '../models/transaction.dart';

class DBHelper {
  static Database? _db;

  static Future<Database> get db async {
    _db ??= await _initDB();
    return _db!;
  }

  static Future<Database> _initDB() async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, 'pos_data.db');
    return openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE customers (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
          )
        ''');
        await db.execute('''
          CREATE TABLE transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            type        TEXT,
            amount      REAL,
            note        TEXT,
            dt          TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
          )
        ''');
      },
    );
  }

  // ── Customers ──────────────────────────────────────────────────────────────

  static Future<List<Customer>> getCustomers() async {
    final d = await db;
    final rows = await d.query('customers', orderBy: 'name COLLATE NOCASE');
    return rows.map((r) => Customer.fromMap(r)).toList();
  }

  static Future<bool> addCustomer(String name) async {
    try {
      final d = await db;
      await d.insert('customers', {'name': name.trim()});
      return true;
    } catch (_) {
      return false;
    }
  }

  static Future<bool> renameCustomer(int id, String newName) async {
    try {
      final d = await db;
      await d.update('customers', {'name': newName.trim()},
          where: 'id = ?', whereArgs: [id]);
      return true;
    } catch (_) {
      return false;
    }
  }

  static Future<void> deleteCustomer(int id) async {
    final d = await db;
    await d.delete('transactions', where: 'customer_id = ?', whereArgs: [id]);
    await d.delete('customers', where: 'id = ?', whereArgs: [id]);
  }

  // ── Transactions ───────────────────────────────────────────────────────────

  static Future<List<PosTransaction>> getTransactions(
    int customerId, {
    DateTime? from,
    DateTime? to,
  }) async {
    final d = await db;
    String where = 'customer_id = ?';
    List<dynamic> args = [customerId];
    if (from != null) {
      where += ' AND dt >= ?';
      args.add('${from.toIso8601String().substring(0, 10)} 00:00:00');
    }
    if (to != null) {
      where += ' AND dt <= ?';
      args.add('${to.toIso8601String().substring(0, 10)} 23:59:59');
    }
    final rows = await d.query(
      'transactions',
      where: where,
      whereArgs: args,
      orderBy: 'dt ASC, id ASC',
    );
    return rows.map((r) => PosTransaction.fromMap(r)).toList();
  }

  static Future<void> addTransaction({
    required int customerId,
    required String type,
    required double amount,
    required String note,
    required DateTime dt,
  }) async {
    final d = await db;
    await d.insert('transactions', {
      'customer_id': customerId,
      'type': type,
      'amount': amount,
      'note': note,
      'dt': dt.toIso8601String().substring(0, 19).replaceAll('T', ' '),
    });
  }

  static Future<void> editTransaction(
      int id, double amount, String note) async {
    final d = await db;
    await d.update(
      'transactions',
      {'amount': amount, 'note': note},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  static Future<void> deleteTransaction(int id) async {
    final d = await db;
    await d.delete('transactions', where: 'id = ?', whereArgs: [id]);
  }

  // ── Balance helpers ────────────────────────────────────────────────────────

  static Future<double> getBalance(int customerId,
      {DateTime? from, DateTime? to}) async {
    final txs = await getTransactions(customerId, from: from, to: to);
    return txs.fold(0.0, (sum, t) =>
        sum + (t.type == 'Deposit' ? t.amount : -t.amount));
  }

  static Future<double> getTotalBalance() async {
    final customers = await getCustomers();
    double total = 0;
    for (final c in customers) {
      total += await getBalance(c.id);
    }
    return total;
  }
}
