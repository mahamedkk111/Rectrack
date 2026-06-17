import 'dart:io';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:share_plus/share_plus.dart';
import 'package:excel/excel.dart' as xl;
import 'package:csv/csv.dart';
import '../db/db_helper.dart';
import '../models/customer.dart';
import '../models/transaction.dart';

const kBusinessName = 'M KK BIZ HUB';
final _fmt = NumberFormat('#,##0.00');
String fmtAmt(double v) => _fmt.format(v);

class ExportService {
  // ── Get save directory ─────────────────────────────────────────────────────
  static Future<Directory> _saveDir() async {
    if (Platform.isAndroid) {
      return Directory('/storage/emulated/0/Download');
    }
    return await getApplicationDocumentsDirectory();
  }

  // ── PDF ────────────────────────────────────────────────────────────────────
  static Future<String> exportPdf(
    Customer customer, {
    DateTime? from,
    DateTime? to,
    bool share = false,
  }) async {
    final txs = await DBHelper.getTransactions(customer.id, from: from, to: to);

    // Opening balance (sum of all transactions before date_from)
    double opening = 0;
    if (from != null) {
      final allTxs = await DBHelper.getTransactions(customer.id);
      for (final t in allTxs) {
        if (t.dt.isBefore(from)) {
          opening += t.type == 'Deposit' ? t.amount : -t.amount;
        }
      }
    }

    double totalIn  = 0, totalOut = 0, running = opening;
    for (final t in txs) {
      if (t.type == 'Deposit') { totalIn  += t.amount; }
      else                     { totalOut += t.amount; }
    }
    final closing = opening + totalIn - totalOut;

    final now = DateTime.now();
    final generated = DateFormat('yyyy-MM-dd HH:mm').format(now);
    final periodStr = (from == null && to == null)
        ? 'All Dates'
        : '${from != null ? DateFormat('yyyy-MM-dd').format(from) : '—'}'
          '  to  '
          '${to != null ? DateFormat('yyyy-MM-dd').format(to) : '—'}';

    // ── Build PDF ─────────────────────────────────────────────────────────
    final pdf = pw.Document();
    const darkBlue  = PdfColor.fromInt(0xFF1A237E);
    const midBlue   = PdfColor.fromInt(0xFF283593);
    const lightRow  = PdfColor.fromInt(0xFFE8EAF6);
    const altRow    = PdfColor.fromInt(0xFFF5F5F5);
    const green     = PdfColor.fromInt(0xFF2E7D32);
    const red       = PdfColor.fromInt(0xFFC62828);
    const greyLine  = PdfColor.fromInt(0xFF9E9E9E);

    pdf.addPage(pw.MultiPage(
      pageFormat: PdfPageFormat.a4,
      margin: const pw.EdgeInsets.all(15 * PdfPageFormat.mm),
      build: (ctx) {
        return [
          // ── Header ──────────────────────────────────────────────────────
          pw.Container(
            color: darkBlue,
            padding: const pw.EdgeInsets.symmetric(vertical: 12, horizontal: 16),
            child: pw.Center(
              child: pw.Text(
                kBusinessName,
                style: pw.TextStyle(
                  fontSize: 22,
                  fontWeight: pw.FontWeight.bold,
                  color: PdfColors.white,
                ),
              ),
            ),
          ),
          pw.Container(
            color: midBlue,
            padding: const pw.EdgeInsets.symmetric(vertical: 6),
            child: pw.Center(
              child: pw.Text(
                'ACCOUNT STATEMENT',
                style: pw.TextStyle(
                  fontSize: 11,
                  fontWeight: pw.FontWeight.bold,
                  color: PdfColors.white,
                ),
              ),
            ),
          ),
          pw.SizedBox(height: 10),

          // ── Summary box ──────────────────────────────────────────────────
          pw.Container(
            decoration: pw.BoxDecoration(
              color: lightRow,
              border: pw.Border.all(color: greyLine, width: 0.5),
            ),
            child: pw.Table(
              children: [
                _summaryRow('Account Holder', customer.name,
                    'Issued By', kBusinessName),
                _summaryRow('Period', periodStr,
                    'Generated', generated),
                _summaryRow('Opening Balance', fmtAmt(opening),
                    'Closing Balance', fmtAmt(closing)),
                _summaryRow(
                  'Total Deposits', fmtAmt(totalIn),
                  'Total Withdrawals', fmtAmt(totalOut),
                  v1Color: green, v2Color: red,
                ),
              ],
            ),
          ),
          pw.SizedBox(height: 10),

          // ── Transactions table ────────────────────────────────────────────
          pw.Table(
            columnWidths: {
              0: const pw.FlexColumnWidth(1.4),
              1: const pw.FlexColumnWidth(0.9),
              2: const pw.FlexColumnWidth(1.1),
              3: const pw.FlexColumnWidth(1.2),
              4: const pw.FlexColumnWidth(2.8),
              5: const pw.FlexColumnWidth(1.3),
              6: const pw.FlexColumnWidth(0.6),
            },
            children: [
              // Header row
              pw.TableRow(
                decoration: const pw.BoxDecoration(color: darkBlue),
                children: ['Date','Time','Type','Amount','Note','Running','Ref#']
                    .map((h) => pw.Padding(
                          padding: const pw.EdgeInsets.all(4),
                          child: pw.Text(h,
                              style: pw.TextStyle(
                                  color: PdfColors.white,
                                  fontSize: 8,
                                  fontWeight: pw.FontWeight.bold)),
                        ))
                    .toList(),
              ),
              // Data rows
              ...txs.asMap().entries.map((e) {
                final i = e.key;
                final t = e.value;
                running += t.type == 'Deposit' ? t.amount : -t.amount;
                final isDeposit = t.type == 'Deposit';
                final bg = i.isEven ? PdfColors.white : altRow;
                return pw.TableRow(
                  decoration: pw.BoxDecoration(color: bg),
                  children: [
                    _cell(DateFormat('yyyy-MM-dd').format(t.dt)),
                    _cell(DateFormat('HH:mm').format(t.dt)),
                    _cell(t.type),
                    _cell(
                      '${isDeposit ? '+' : '-'}${fmtAmt(t.amount)}',
                      color: isDeposit ? green : red,
                      bold: true,
                    ),
                    _cell(t.note, fontSize: 7),
                    _cell(
                      fmtAmt(running),
                      color: running >= 0 ? green : red,
                      bold: true,
                    ),
                    _cell('${i + 1}',
                        color: greyLine, fontSize: 7),
                  ],
                );
              }),
              if (txs.isEmpty)
                pw.TableRow(children: [
                  pw.Padding(
                    padding: const pw.EdgeInsets.all(8),
                    child: pw.Text('No transactions in this period.',
                        style: const pw.TextStyle(fontSize: 8)),
                  ),
                  ...List.generate(6, (_) => pw.SizedBox()),
                ]),
            ],
          ),
          pw.SizedBox(height: 10),

          // ── Footer ────────────────────────────────────────────────────────
          pw.Divider(color: greyLine),
          pw.SizedBox(height: 4),
          pw.Center(
            child: pw.Text(
              'This statement was generated by $kBusinessName on $generated. '
              'For queries, contact your account manager.',
              style: pw.TextStyle(
                  fontSize: 7,
                  color: greyLine,
                  fontStyle: pw.FontStyle.italic),
            ),
          ),
        ];
      },
    ));

    final dir  = await _saveDir();
    final safe = customer.name.replaceAll(' ', '_');
    final path = '${dir.path}/${safe}_statement.pdf';
    final file = File(path);
    await file.writeAsBytes(await pdf.save());

    if (share) {
      await Share.shareXFiles([XFile(path)],
          subject: '$kBusinessName — ${customer.name} Statement');
    }
    return path;
  }

  static pw.TableRow _summaryRow(
    String l1, String v1, String l2, String v2, {
    PdfColor? v1Color, PdfColor? v2Color,
  }) {
    return pw.TableRow(children: [
      _infoCell(l1, v1, valColor: v1Color),
      _infoCell(l2, v2, valColor: v2Color),
    ]);
  }

  static pw.Widget _infoCell(String label, String value,
      {PdfColor? valColor}) {
    return pw.Padding(
      padding: const pw.EdgeInsets.all(5),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Text(label,
              style: const pw.TextStyle(
                  fontSize: 7, color: PdfColors.grey700)),
          pw.Text(value,
              style: pw.TextStyle(
                  fontSize: 9,
                  fontWeight: pw.FontWeight.bold,
                  color: valColor ?? PdfColors.black)),
        ],
      ),
    );
  }

  static pw.Widget _cell(String text,
      {PdfColor? color, bool bold = false, double fontSize = 8}) {
    return pw.Padding(
      padding: const pw.EdgeInsets.all(4),
      child: pw.Text(
        text,
        style: pw.TextStyle(
          fontSize: fontSize,
          color: color ?? PdfColors.black,
          fontWeight: bold ? pw.FontWeight.bold : pw.FontWeight.normal,
        ),
      ),
    );
  }

  // ── CSV ────────────────────────────────────────────────────────────────────
  static Future<String> exportCsv(
    Customer customer, {
    DateTime? from,
    DateTime? to,
    bool share = false,
  }) async {
    final txs = await DBHelper.getTransactions(customer.id, from: from, to: to);
    double running = 0;
    final rows = <List<dynamic>>[
      ['Date', 'Time', 'Type', 'Amount', 'Note', 'Running Balance'],
    ];
    for (final t in txs) {
      running += t.type == 'Deposit' ? t.amount : -t.amount;
      rows.add([
        DateFormat('yyyy-MM-dd').format(t.dt),
        DateFormat('HH:mm:ss').format(t.dt),
        t.type,
        t.amount,
        t.note,
        running,
      ]);
    }
    final csv  = const ListToCsvConverter().convert(rows);
    final dir  = await _saveDir();
    final safe = customer.name.replaceAll(' ', '_');
    final path = '${dir.path}/${safe}_transactions.csv';
    await File(path).writeAsString(csv);
    if (share) {
      await Share.shareXFiles([XFile(path)],
          subject: '$kBusinessName — ${customer.name} Transactions');
    }
    return path;
  }

  static Future<String> exportAllCsv({bool share = false}) async {
    final customers = await DBHelper.getCustomers();
    final rows = <List<dynamic>>[['Customer Name', 'Balance']];
    final balances = <MapEntry<String, double>>[];
    for (final c in customers) {
      final bal = await DBHelper.getBalance(c.id);
      balances.add(MapEntry(c.name, bal));
    }
    balances.sort((a, b) => b.value.compareTo(a.value));
    for (final e in balances) {
      rows.add([e.key, fmtAmt(e.value)]);
    }
    final csv  = const ListToCsvConverter().convert(rows);
    final dir  = await _saveDir();
    final path = '${dir.path}/all_customers_balances.csv';
    await File(path).writeAsString(csv);
    if (share) {
      await Share.shareXFiles([XFile(path)],
          subject: '$kBusinessName — All Balances');
    }
    return path;
  }

  // ── Excel ──────────────────────────────────────────────────────────────────
  static Future<String> exportExcel(
    Customer customer, {
    DateTime? from,
    DateTime? to,
    bool share = false,
  }) async {
    final txs  = await DBHelper.getTransactions(customer.id, from: from, to: to);
    final excel = xl.Excel.createExcel();
    final sheet = excel['Transactions'];
    sheet.appendRow(['Date','Time','Type','Amount','Note','Running Balance']
        .map((e) => xl.TextCellValue(e)).toList());
    double running = 0;
    for (final t in txs) {
      running += t.type == 'Deposit' ? t.amount : -t.amount;
      sheet.appendRow([
        xl.TextCellValue(DateFormat('yyyy-MM-dd').format(t.dt)),
        xl.TextCellValue(DateFormat('HH:mm:ss').format(t.dt)),
        xl.TextCellValue(t.type),
        xl.DoubleCellValue(t.amount),
        xl.TextCellValue(t.note),
        xl.DoubleCellValue(running),
      ]);
    }
    final dir   = await _saveDir();
    final safe  = customer.name.replaceAll(' ', '_');
    final path  = '${dir.path}/${safe}_transactions.xlsx';
    final bytes = excel.save()!;
    await File(path).writeAsBytes(bytes);
    if (share) {
      await Share.shareXFiles([XFile(path)],
          subject: '$kBusinessName — ${customer.name} Transactions');
    }
    return path;
  }

  static Future<String> exportAllExcel({bool share = false}) async {
    final customers = await DBHelper.getCustomers();
    final excel = xl.Excel.createExcel();
    final sheet = excel['Balances'];
    sheet.appendRow(['Customer Name', 'Balance']
        .map((e) => xl.TextCellValue(e)).toList());
    final balances = <MapEntry<String, double>>[];
    for (final c in customers) {
      final bal = await DBHelper.getBalance(c.id);
      balances.add(MapEntry(c.name, bal));
    }
    balances.sort((a, b) => b.value.compareTo(a.value));
    for (final e in balances) {
      sheet.appendRow([
        xl.TextCellValue(e.key),
        xl.DoubleCellValue(e.value),
      ]);
    }
    final dir   = await _saveDir();
    final path  = '${dir.path}/all_customers_balances.xlsx';
    final bytes = excel.save()!;
    await File(path).writeAsBytes(bytes);
    if (share) {
      await Share.shareXFiles([XFile(path)],
          subject: '$kBusinessName — All Balances');
    }
    return path;
  }
}
