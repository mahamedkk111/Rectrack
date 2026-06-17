import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:animations/animations.dart';
import '../db/db_helper.dart';
import '../models/customer.dart';
import '../services/export_service.dart';
import 'customer_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Customer>     _customers    = [];
  Map<int, double>   _balances     = {};
  double             _totalBalance = 0;
  String             _search       = '';
  Customer?          _selected;

  final _addCtrl    = TextEditingController();
  final _amtCtrl    = TextEditingController();
  final _noteCtrl   = TextEditingController();
  final _searchCtrl = TextEditingController();
  final _fmt        = NumberFormat('#,##0.00');

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _addCtrl.dispose();
    _amtCtrl.dispose();
    _noteCtrl.dispose();
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final customers = await DBHelper.getCustomers();
    final balances  = <int, double>{};
    double total    = 0;
    for (final c in customers) {
      final b = await DBHelper.getBalance(c.id);
      balances[c.id] = b;
      total += b;
    }
    // Sort by balance descending
    customers.sort(
        (a, b) => (balances[b.id] ?? 0).compareTo(balances[a.id] ?? 0));
    if (mounted) {
      setState(() {
        _customers    = customers;
        _balances     = balances;
        _totalBalance = total;
        if (_selected != null) {
          _selected = customers.firstWhere(
            (c) => c.id == _selected!.id,
            orElse: () => customers.isNotEmpty ? customers.first : _selected!,
          );
        }
      });
    }
  }

  List<Customer> get _filtered => _customers
      .where((c) => c.name.toLowerCase().contains(_search.toLowerCase()))
      .toList();

  String _fmt2(double v) => _fmt.format(v);

  // ── Snackbar ───────────────────────────────────────────────────────────────
  void _snack(String msg, {Color? color}) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg, style: const TextStyle(fontSize: 13)),
      backgroundColor: color ?? const Color(0xFF1565C0),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      duration: const Duration(seconds: 2),
    ));
  }

  // ── Add customer ───────────────────────────────────────────────────────────
  Future<void> _addCustomer() async {
    final name = _addCtrl.text.trim();
    if (name.isEmpty) { _snack('Enter a name'); return; }
    final ok = await DBHelper.addCustomer(name);
    if (ok) {
      _addCtrl.clear();
      await _load();
      _snack("'$name' added");
    } else {
      _snack("'$name' already exists", color: Colors.orange);
    }
  }

  // ── Add transaction ────────────────────────────────────────────────────────
  Future<void> _addTransaction(String type) async {
    if (_selected == null) {
      _snack('Tap a customer first', color: Colors.orange);
      return;
    }
    final amt = double.tryParse(_amtCtrl.text.trim());
    if (amt == null || amt <= 0) {
      _snack('Enter a valid amount', color: Colors.orange);
      return;
    }
    await DBHelper.addTransaction(
      customerId: _selected!.id,
      type: type,
      amount: amt,
      note: _noteCtrl.text.trim(),
      dt: DateTime.now(),
    );
    _amtCtrl.clear();
    _noteCtrl.clear();
    await _load();
    _snack('$type ${_fmt2(amt)} added for ${_selected!.name}');
  }

  // ── Customer menu ──────────────────────────────────────────────────────────
  void _openMenu(Customer c) {
    setState(() => _selected = c);
    final bal     = _balances[c.id] ?? 0;
    final balColor = bal >= 0 ? Colors.greenAccent : Colors.redAccent;

    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1A1A2E),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (_) => _CustomerMenu(
        customer: c,
        balance: bal,
        balColor: balColor,
        onDetails: () {
          Navigator.pop(context);
          _goDetails(c);
        },
        onCIn:  () { Navigator.pop(context); _addTransaction('Deposit');  },
        onCOut: () { Navigator.pop(context); _addTransaction('Withdraw'); },
        onExportPdf:   (share) => _exportPdf(c, share: share),
        onExportCsv:   (share) => _exportCsv(c, share: share),
        onExportExcel: (share) => _exportExcel(c, share: share),
        onRename: () {
          Navigator.pop(context);
          _renameDialog(c);
        },
        onDelete: () {
          Navigator.pop(context);
          _deleteDialog(c);
        },
      ),
    );
  }

  void _goDetails(Customer c) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => CustomerScreen(customer: c)),
    ).then((_) => _load());
  }

  // ── Export helpers ─────────────────────────────────────────────────────────
  Future<void> _exportPdf(Customer c, {bool share = false}) async {
    try {
      final path = await ExportService.exportPdf(c, share: share);
      if (!share) _snack('PDF saved: $path');
    } catch (e) {
      _snack('Error: $e', color: Colors.red);
    }
  }

  Future<void> _exportCsv(Customer c, {bool share = false}) async {
    try {
      final path = await ExportService.exportCsv(c, share: share);
      if (!share) _snack('CSV saved: $path');
    } catch (e) {
      _snack('Error: $e', color: Colors.red);
    }
  }

  Future<void> _exportExcel(Customer c, {bool share = false}) async {
    try {
      final path = await ExportService.exportExcel(c, share: share);
      if (!share) _snack('Excel saved: $path');
    } catch (e) {
      _snack('Error: $e', color: Colors.red);
    }
  }

  Future<void> _exportAllCsv({bool share = false}) async {
    try {
      final path = await ExportService.exportAllCsv(share: share);
      if (!share) _snack('CSV saved: $path');
    } catch (e) {
      _snack('Error: $e', color: Colors.red);
    }
  }

  Future<void> _exportAllExcel({bool share = false}) async {
    try {
      final path = await ExportService.exportAllExcel(share: share);
      if (!share) _snack('Excel saved: $path');
    } catch (e) {
      _snack('Error: $e', color: Colors.red);
    }
  }

  // ── Rename dialog ──────────────────────────────────────────────────────────
  void _renameDialog(Customer c) {
    final ctrl = TextEditingController(text: c.name);
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: const Color(0xFF1A1A2E),
        title: const Text('Rename Customer'),
        content: TextField(
          controller: ctrl,
          decoration: const InputDecoration(labelText: 'New name'),
          autofocus: true,
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              final ok = await DBHelper.renameCustomer(c.id, ctrl.text);
              Navigator.pop(context);
              if (ok) {
                await _load();
                _snack('Renamed to ${ctrl.text}');
              } else {
                _snack('Name already exists', color: Colors.orange);
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  // ── Delete dialog ──────────────────────────────────────────────────────────
  void _deleteDialog(Customer c) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: const Color(0xFF1A1A2E),
        title: const Text('Delete Customer'),
        content: Text(
            "Delete '${c.name}' and all their transactions? This cannot be undone."),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () async {
              await DBHelper.deleteCustomer(c.id);
              Navigator.pop(context);
              if (_selected?.id == c.id) setState(() => _selected = null);
              await _load();
              _snack("'${c.name}' deleted", color: Colors.red);
            },
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  // ── Export all bottom sheet ────────────────────────────────────────────────
  void _exportAllMenu() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1A1A2E),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Export All Balances',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            _exportTile(Icons.table_chart, 'Save CSV', Colors.teal,
                () { Navigator.pop(context); _exportAllCsv(); }),
            _exportTile(Icons.grid_on, 'Save Excel', Colors.purple,
                () { Navigator.pop(context); _exportAllExcel(); }),
            _exportTile(Icons.share, 'Share CSV', Colors.teal.shade300,
                () { Navigator.pop(context); _exportAllCsv(share: true); }),
            _exportTile(Icons.share, 'Share Excel', Colors.purple.shade300,
                () { Navigator.pop(context); _exportAllExcel(share: true); }),
          ],
        ),
      ),
    );
  }

  Widget _exportTile(IconData icon, String label, Color color, VoidCallback cb) {
    return ListTile(
      leading: Icon(icon, color: color),
      title: Text(label, style: const TextStyle(fontSize: 14)),
      onTap: cb,
      dense: true,
    );
  }

  // ── Build ──────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final totalColor = _totalBalance >= 0
        ? Colors.greenAccent.shade400
        : Colors.redAccent;

    return Scaffold(
      resizeToAvoidBottomInset: true,   // keyboard pushes content up
      appBar: AppBar(
        title: const Text('M KK BIZ HUB',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        actions: [
          IconButton(
            icon: const Icon(Icons.file_download),
            tooltip: 'Export All',
            onPressed: _exportAllMenu,
          ),
        ],
      ),

      body: Column(
        children: [
          // ── Total balance banner ─────────────────────────────────────────
          Container(
            width: double.infinity,
            color: const Color(0xFF0D1B3E),
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Total Balance',
                    style: TextStyle(color: Colors.white70, fontSize: 12)),
                Text(_fmt2(_totalBalance),
                    style: TextStyle(
                        color: totalColor,
                        fontSize: 18,
                        fontWeight: FontWeight.bold)),
              ],
            ),
          ),

          // ── Input area ───────────────────────────────────────────────────
          Container(
            color: const Color(0xFF13132A),
            padding: const EdgeInsets.fromLTRB(10, 10, 10, 6),
            child: Column(
              children: [
                // Add customer row
                Row(children: [
                  Expanded(
                    child: TextField(
                      controller: _addCtrl,
                      decoration: const InputDecoration(
                          hintText: 'New customer name',
                          hintStyle: TextStyle(fontSize: 12),
                          isDense: true),
                      style: const TextStyle(fontSize: 13),
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => _addCustomer(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: _addCustomer,
                    style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green.shade700),
                    child: const Text('ADD', style: TextStyle(fontSize: 12)),
                  ),
                ]),
                const SizedBox(height: 8),
                // Search row
                TextField(
                  controller: _searchCtrl,
                  decoration: InputDecoration(
                    hintText: 'Search customer…',
                    hintStyle: const TextStyle(fontSize: 12),
                    isDense: true,
                    prefixIcon: const Icon(Icons.search, size: 18),
                    suffixIcon: _search.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear, size: 16),
                            onPressed: () {
                              _searchCtrl.clear();
                              setState(() => _search = '');
                            })
                        : null,
                  ),
                  style: const TextStyle(fontSize: 13),
                  onChanged: (v) => setState(() => _search = v),
                ),
                const SizedBox(height: 8),
                // Amount + Note + buttons
                Row(children: [
                  Expanded(
                    flex: 3,
                    child: TextField(
                      controller: _amtCtrl,
                      decoration: const InputDecoration(
                          hintText: 'Amount',
                          hintStyle: TextStyle(fontSize: 12),
                          isDense: true),
                      style: const TextStyle(fontSize: 13),
                      keyboardType: const TextInputType.numberWithOptions(
                          decimal: true),
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(
                            RegExp(r'^\d*\.?\d*'))
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    flex: 4,
                    child: TextField(
                      controller: _noteCtrl,
                      decoration: const InputDecoration(
                          hintText: 'Note (optional)',
                          hintStyle: TextStyle(fontSize: 12),
                          isDense: true),
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                  const SizedBox(width: 6),
                  ElevatedButton(
                    onPressed: () => _addTransaction('Deposit'),
                    style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green.shade700,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 10)),
                    child: const Text('C IN',
                        style: TextStyle(fontSize: 11)),
                  ),
                  const SizedBox(width: 4),
                  ElevatedButton(
                    onPressed: () => _addTransaction('Withdraw'),
                    style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange.shade700,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 10)),
                    child: const Text('C OUT',
                        style: TextStyle(fontSize: 11)),
                  ),
                ]),
                // Selected customer indicator
                if (_selected != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Row(children: [
                      const Icon(Icons.person_pin,
                          size: 14, color: Colors.blueAccent),
                      const SizedBox(width: 4),
                      Text(
                        'Selected: ${_selected!.name}',
                        style: const TextStyle(
                            fontSize: 11, color: Colors.blueAccent),
                      ),
                      const Spacer(),
                      GestureDetector(
                        onTap: () => setState(() => _selected = null),
                        child: const Icon(Icons.close,
                            size: 14, color: Colors.grey),
                      ),
                    ]),
                  ),
              ],
            ),
          ),

          // ── Customer list header ─────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 8, 14, 4),
            child: Row(
              children: [
                Text(
                  'Customers (${_filtered.length})',
                  style: const TextStyle(
                      fontSize: 12, color: Colors.white54),
                ),
                const Spacer(),
                const Text('Balance',
                    style: TextStyle(fontSize: 12, color: Colors.white54)),
              ],
            ),
          ),

          // ── Customer list ────────────────────────────────────────────────
          Expanded(
            child: _filtered.isEmpty
                ? const Center(
                    child: Text('No customers found.',
                        style: TextStyle(color: Colors.white38)))
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(10, 0, 10, 80),
                    itemCount: _filtered.length,
                    itemBuilder: (_, i) {
                      final c   = _filtered[i];
                      final bal = _balances[c.id] ?? 0;
                      final isSelected = _selected?.id == c.id;
                      return _CustomerTile(
                        customer:   c,
                        balance:    bal,
                        isSelected: isSelected,
                        onTap:      () => _openMenu(c),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

// ── Customer tile ─────────────────────────────────────────────────────────────
class _CustomerTile extends StatelessWidget {
  final Customer customer;
  final double   balance;
  final bool     isSelected;
  final VoidCallback onTap;

  const _CustomerTile({
    required this.customer,
    required this.balance,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final balColor = balance >= 0
        ? Colors.greenAccent.shade400
        : Colors.redAccent;
    final fmt = NumberFormat('#,##0.00');

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        margin: const EdgeInsets.only(bottom: 4),
        decoration: BoxDecoration(
          color: isSelected
              ? const Color(0xFF1A237E).withOpacity(0.5)
              : const Color(0xFF1A1A2E),
          borderRadius: BorderRadius.circular(8),
          border: isSelected
              ? Border.all(color: Colors.blueAccent, width: 1.2)
              : null,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            Expanded(
              child: Text(
                customer.name,
                style: const TextStyle(
                    fontSize: 13, fontWeight: FontWeight.w600),
              ),
            ),
            Text(
              fmt.format(balance),
              style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: balColor),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Customer bottom-sheet menu ────────────────────────────────────────────────
class _CustomerMenu extends StatelessWidget {
  final Customer   customer;
  final double     balance;
  final Color      balColor;
  final VoidCallback onDetails;
  final VoidCallback onCIn;
  final VoidCallback onCOut;
  final Function(bool share) onExportPdf;
  final Function(bool share) onExportCsv;
  final Function(bool share) onExportExcel;
  final VoidCallback onRename;
  final VoidCallback onDelete;

  const _CustomerMenu({
    required this.customer,
    required this.balance,
    required this.balColor,
    required this.onDetails,
    required this.onCIn,
    required this.onCOut,
    required this.onExportPdf,
    required this.onExportCsv,
    required this.onExportExcel,
    required this.onRename,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final fmt = NumberFormat('#,##0.00');
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle
          Container(
              width: 36, height: 4,
              decoration: BoxDecoration(
                  color: Colors.white24,
                  borderRadius: BorderRadius.circular(2))),
          const SizedBox(height: 12),
          // Header
          Row(
            children: [
              const Icon(Icons.person, color: Colors.blueAccent, size: 22),
              const SizedBox(width: 8),
              Text(customer.name,
                  style: const TextStyle(
                      fontSize: 16, fontWeight: FontWeight.bold)),
              const Spacer(),
              Text(fmt.format(balance),
                  style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: balColor)),
            ],
          ),
          const Divider(height: 20),
          // Action grid
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _menuBtn('Details',    Icons.list_alt,       Colors.blue,         onDetails),
              _menuBtn('C IN',       Icons.add_circle,     Colors.green,        onCIn),
              _menuBtn('C OUT',      Icons.remove_circle,  Colors.orange,       onCOut),
              _menuBtn('Save PDF',   Icons.picture_as_pdf, Colors.red,          () { Navigator.pop(context); onExportPdf(false); }),
              _menuBtn('Share PDF',  Icons.share,          Colors.red.shade300, () { Navigator.pop(context); onExportPdf(true); }),
              _menuBtn('Save CSV',   Icons.table_chart,    Colors.teal,         () { Navigator.pop(context); onExportCsv(false); }),
              _menuBtn('Share CSV',  Icons.share,          Colors.teal.shade300,() { Navigator.pop(context); onExportCsv(true); }),
              _menuBtn('Save Excel', Icons.grid_on,        Colors.purple,       () { Navigator.pop(context); onExportExcel(false); }),
              _menuBtn('Share Excel',Icons.share,          Colors.purple.shade300,() { Navigator.pop(context); onExportExcel(true); }),
              _menuBtn('Rename',     Icons.edit,           Colors.amber,        onRename),
              _menuBtn('Delete',     Icons.delete,         Colors.red.shade800, onDelete),
            ],
          ),
        ],
      ),
    );
  }

  Widget _menuBtn(String label, IconData icon, Color color, VoidCallback cb) {
    return GestureDetector(
      onTap: cb,
      child: Container(
        width: 84,
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
        decoration: BoxDecoration(
          color: color.withOpacity(0.15),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withOpacity(0.4)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(height: 4),
            Text(label,
                textAlign: TextAlign.center,
                style: TextStyle(
                    fontSize: 10,
                    color: color,
                    fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}
