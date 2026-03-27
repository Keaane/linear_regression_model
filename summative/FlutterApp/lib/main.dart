import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'dart:ui';

void main() {
  runApp(const CropYieldPredictorApp());
}

class CropYieldPredictorApp extends StatelessWidget {
  const CropYieldPredictorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Crop Yield Predictor',
      theme: ThemeData(
        primaryColor: const Color(0xFF4ADE80),
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4ADE80)),
        textTheme: GoogleFonts.poppinsTextTheme(Theme.of(context).textTheme),
        scaffoldBackgroundColor: Colors.transparent,
        appBarTheme: const AppBarTheme(backgroundColor: Colors.transparent, foregroundColor: Colors.white),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white.withValues(alpha: 0.08),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.22)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0xFFBBF7D0), width: 1.6),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0xFFFCA5A5)),
          ),
          focusedErrorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0xFFFCA5A5), width: 1.6),
          ),
          labelStyle: TextStyle(color: Colors.white.withValues(alpha: 0.92)),
          hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.74)),
        ),
      ),
      home: const PredictionPage(),
    );
  }
}

class PredictionPage extends StatefulWidget {
  const PredictionPage({super.key});

  @override
  State<PredictionPage> createState() => _PredictionPageState();
}

class _PredictionPageState extends State<PredictionPage> {
  final _formKey = GlobalKey<FormState>();

  final List<String> validAreas = [
    "Albania", "Algeria", "Angola", "Argentina", "Armenia", "Australia", 
    "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Belarus", 
    "Belgium", "Botswana", "Brazil", "Bulgaria", "Burkina Faso", "Burundi", 
    "Cameroon", "Canada", "Central African Republic", "Chile", "Colombia", 
    "Croatia", "Denmark", "Dominican Republic", "Ecuador", "Egypt", 
    "El Salvador", "Eritrea", "Estonia", "Finland", "France", "Germany", 
    "Ghana", "Greece", "Guatemala", "Guinea", "Guyana", "Haiti", "Honduras", 
    "Hungary", "India", "Indonesia", "Iraq", "Ireland", "Italy", "Jamaica", 
    "Japan", "Kazakhstan", "Kenya", "Latvia", "Lebanon", "Lesotho", "Libya", 
    "Lithuania", "Madagascar", "Malawi", "Malaysia", "Mali", "Mauritania", 
    "Mauritius", "Mexico", "Montenegro", "Morocco", "Mozambique", "Namibia", 
    "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Norway", 
    "Pakistan", "Papua New Guinea", "Peru", "Poland", "Portugal", "Qatar", 
    "Romania", "Rwanda", "Saudi Arabia", "Senegal", "Slovenia", "South Africa", 
    "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", 
    "Tajikistan", "Thailand", "Tunisia", "Turkey", "Uganda", "Ukraine", 
    "United Kingdom", "Uruguay", "Zambia", "Zimbabwe"
  ];

  final List<String> validCrops = [
    "Cassava", "Maize", "Plantains and others", "Potatoes", "Rice paddy", 
    "Sorghum", "Soybeans", "Sweet potatoes", "Wheat", "Yams"
  ];

  String? _selectedArea;
  String? _selectedCrop;
  final TextEditingController _yearController = TextEditingController();
  final TextEditingController _rainController = TextEditingController();
  final TextEditingController _tempController = TextEditingController();
  final TextEditingController _pesticideController = TextEditingController();

  bool _isLoading = false;
  String? _predictionResult;
  String? _errorMessage;

  void _submitForm() async {
    if (_formKey.currentState!.validate()) {
      setState(() {
        _isLoading = true;
        _predictionResult = null;
        _errorMessage = null;
      });

      try {
        final requestBody = jsonEncode({
          "area": _selectedArea,
          "item": _selectedCrop,
          "year": int.parse(_yearController.text),
          "average_rain_fall_mm_per_year": double.parse(_rainController.text),
          "pesticides_tonnes": double.parse(_pesticideController.text),
          "avg_temp": double.parse(_tempController.text),
        });

       final url = Uri.parse('https://crop-yield-predictor-api-nhma.onrender.com/predict');
        
        final response = await http.post(
          url,
          headers: {"Content-Type": "application/json"},
          body: requestBody,
        ).timeout(const Duration(seconds: 30));

        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final yieldHg = data['predicted_yield_hg_per_ha'] as num;
          final yieldTonnes = yieldHg / 10000;
          
          setState(() {
            _predictionResult = "${yieldHg.toStringAsFixed(2).replaceAll(RegExp(r'\B(?=(\d{3})+(?!\d))'), ',')} hg/ha\n"
                "${yieldTonnes.toStringAsFixed(4)} t/ha";
          });
        } else {
          final data = jsonDecode(response.body);
          setState(() {
            _errorMessage = data['detail']?.toString() ?? 'Server error ${response.statusCode}';
          });
        }
      } on TimeoutException {
        setState(() {
          _errorMessage = "Request timed out after 30 seconds.";
        });
      } catch (e) {
        setState(() {
          _errorMessage = e.toString();
        });
      } finally {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10, top: 6),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 16,
            decoration: BoxDecoration(
              color: const Color(0xFFBBF7D0),
              borderRadius: BorderRadius.circular(999),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            title,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: Colors.white.withValues(alpha: 0.94),
              letterSpacing: 1.3,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGlassCard({required Widget child}) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          width: double.infinity,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Colors.white.withValues(alpha: 0.2),
                Colors.white.withValues(alpha: 0.08),
              ],
            ),
            border: Border.all(color: Colors.white.withValues(alpha: 0.35), width: 1.2),
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: child,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        elevation: 0,
        title: const Text(
          'Crop Yield Predictor',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 30,
            letterSpacing: -0.3,
            height: 1.1,
          ),
        ),
      ),
      extendBodyBehindAppBar: true,
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF052E16),
              Color(0xFF14532D),
              Color(0xFF166534),
              Color(0xFF0F766E),
            ],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Predict crop yield using climate and agricultural indicators.',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.9),
                        fontSize: 15,
                        fontWeight: FontWeight.w500,
                        height: 1.35,
                      ),
                    ),
                    const SizedBox(height: 14),
                    _buildSectionHeader("LOCATION & CROP"),
                    _buildGlassCard(
                      child: Column(
                        children: [
                          Autocomplete<String>(
                            optionsBuilder: (TextEditingValue textEditingValue) {
                              if (textEditingValue.text.isEmpty) {
                                return validAreas;
                              }
                              return validAreas.where((String option) {
                                return option.toLowerCase().contains(textEditingValue.text.toLowerCase());
                              });
                            },
                            onSelected: (String selection) {
                              _selectedArea = selection;
                            },
                            fieldViewBuilder: (context, controller, focusNode, onEditingComplete) {
                              controller.addListener(() {
                                _selectedArea = controller.text;
                              });
                              return TextFormField(
                                controller: controller,
                                focusNode: focusNode,
                                style: const TextStyle(color: Colors.white),
                                decoration: const InputDecoration(labelText: 'Country / Region'),
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'Please enter a country/region';
                                  }
                                  if (!validAreas.contains(value)) {
                                    return 'Not a valid country/region';
                                  }
                                  return null;
                                },
                              );
                            },
                          ),
                          const SizedBox(height: 16),
                          Autocomplete<String>(
                            optionsBuilder: (TextEditingValue textEditingValue) {
                              if (textEditingValue.text.isEmpty) {
                                return validCrops;
                              }
                              return validCrops.where((String option) {
                                return option.toLowerCase().contains(textEditingValue.text.toLowerCase());
                              });
                            },
                            onSelected: (String selection) {
                              _selectedCrop = selection;
                            },
                            fieldViewBuilder: (context, controller, focusNode, onEditingComplete) {
                              controller.addListener(() {
                                _selectedCrop = controller.text;
                              });
                              return TextFormField(
                                controller: controller,
                                focusNode: focusNode,
                                style: const TextStyle(color: Colors.white),
                                decoration: const InputDecoration(labelText: 'Crop Type'),
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'Please enter a crop type';
                                  }
                                  if (!validCrops.contains(value)) {
                                    return 'Not a valid crop type';
                                  }
                                  return null;
                                },
                              );
                            },
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    _buildSectionHeader("CLIMATE CONDITIONS"),
                    _buildGlassCard(
                      child: Column(
                        children: [
                          TextFormField(
                            controller: _yearController,
                            keyboardType: TextInputType.number,
                            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                            style: const TextStyle(color: Colors.white),
                            decoration: const InputDecoration(labelText: 'Year'),
                            validator: (value) {
                              if (value == null || value.isEmpty) return 'Please enter a year';
                              final year = int.tryParse(value);
                              if (year == null || year < 1990 || year > 2030) {
                                return 'Year must be between 1990 and 2030';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _rainController,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            style: const TextStyle(color: Colors.white),
                            decoration: const InputDecoration(
                              labelText: 'Annual Rainfall',
                              suffixText: 'mm',
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) return 'Please enter rainfall';
                              final rain = double.tryParse(value);
                              if (rain == null || rain < 51.0 || rain > 3240.0) {
                                return 'Must be between 51.0 and 3240.0 mm';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _tempController,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            style: const TextStyle(color: Colors.white),
                            decoration: const InputDecoration(
                              labelText: 'Average Temperature',
                              suffixText: '°C',
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) return 'Please enter temperature';
                              final temp = double.tryParse(value);
                              if (temp == null || temp < 1.3 || temp > 30.65) {
                                return 'Must be between 1.3 and 30.65 °C';
                              }
                              return null;
                            },
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    _buildSectionHeader("AGRICULTURAL INPUT"),
                    _buildGlassCard(
                      child: TextFormField(
                        controller: _pesticideController,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(
                          labelText: 'Pesticides Used',
                          suffixText: 'tonnes',
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) return 'Please enter pesticide amount';
                          final pest = double.tryParse(value);
                          if (pest == null || pest < 0.0 || pest > 400000.0) {
                            return 'Must be between 0.0 and 400000.0 tonnes';
                          }
                          return null;
                        },
                      ),
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      width: double.infinity,
                      height: 52,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _submitForm,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFFF59E0B),
                          foregroundColor: const Color(0xFF052E16),
                          shadowColor: const Color(0xFF052E16).withValues(alpha: 0.35),
                          elevation: 8,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          side: BorderSide(color: const Color(0xFFFCD34D).withValues(alpha: 0.9)),
                        ),
                        child: _isLoading
                            ? const SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2,
                                ),
                              )
                            : const Text(
                                'Predict',
                                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                              ),
                      ),
                    ),
                    if (_errorMessage != null || _predictionResult != null) ...[
                      const SizedBox(height: 24),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: BackdropFilter(
                          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                          child: Container(
                            width: double.infinity,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(20),
                              gradient: LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: _errorMessage != null
                                    ? [
                                        const Color(0xFF7F1D1D).withValues(alpha: 0.42),
                                        const Color(0xFF991B1B).withValues(alpha: 0.26),
                                      ]
                                    : [
                                        const Color(0xFF14532D).withValues(alpha: 0.44),
                                        const Color(0xFF166534).withValues(alpha: 0.28),
                                      ],
                              ),
                              border: Border.all(
                                color: _errorMessage != null
                                    ? const Color(0xFFFCA5A5).withValues(alpha: 0.7)
                                    : const Color(0xFFBBF7D0).withValues(alpha: 0.7),
                              ),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(20),
                              child: Column(
                                children: [
                                  if (_errorMessage != null)
                                    Column(
                                      children: [
                                        const Icon(Icons.error_outline, color: Color(0xFFFCA5A5), size: 32),
                                        const SizedBox(height: 8),
                                        Text(
                                          _errorMessage!,
                                          style: const TextStyle(
                                            color: Color(0xFFFEE2E2),
                                            fontWeight: FontWeight.w500,
                                          ),
                                          textAlign: TextAlign.center,
                                        ),
                                      ],
                                    ),
                                  if (_predictionResult != null)
                                    Column(
                                      children: [
                                        const Icon(Icons.check_circle_outline, color: Color(0xFFBBF7D0), size: 32),
                                        const SizedBox(height: 8),
                                        Text(
                                          "Estimated Yield",
                                          style: TextStyle(
                                            fontSize: 14,
                                            color: Colors.white.withValues(alpha: 0.88),
                                          ),
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          _predictionResult!,
                                          style: const TextStyle(
                                            fontSize: 22,
                                            fontWeight: FontWeight.bold,
                                            color: Colors.white,
                                          ),
                                          textAlign: TextAlign.center,
                                        ),
                                      ],
                                    ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                    const SizedBox(height: 20),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
