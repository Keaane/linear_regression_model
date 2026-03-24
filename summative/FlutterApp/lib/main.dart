import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

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
        primaryColor: const Color(0xFF2E7D32),
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2E7D32)),
        textTheme: GoogleFonts.poppinsTextTheme(Theme.of(context).textTheme),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF2E7D32),
          foregroundColor: Colors.white,
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
      padding: const EdgeInsets.only(bottom: 8.0, top: 4.0),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: Colors.grey[700],
          letterSpacing: 1.2,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Crop Yield Predictor'),
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildSectionHeader("LOCATION & CROP"),
                Card(
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: BorderSide(color: Colors.grey.shade300),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
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
                              decoration: const InputDecoration(
                                labelText: 'Country / Region',
                                border: OutlineInputBorder(),
                              ),
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
                              decoration: const InputDecoration(
                                labelText: 'Crop Type',
                                border: OutlineInputBorder(),
                              ),
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
                ),
                const SizedBox(height: 20),
                _buildSectionHeader("CLIMATE CONDITIONS"),
                Card(
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: BorderSide(color: Colors.grey.shade300),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      children: [
                        TextFormField(
                          controller: _yearController,
                          keyboardType: TextInputType.number,
                          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                          decoration: const InputDecoration(
                            labelText: 'Year',
                            border: OutlineInputBorder(),
                          ),
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
                          decoration: const InputDecoration(
                            labelText: 'Annual Rainfall',
                            suffixText: 'mm',
                            border: OutlineInputBorder(),
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
                          decoration: const InputDecoration(
                            labelText: 'Average Temperature',
                            suffixText: '°C',
                            border: OutlineInputBorder(),
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
                ),
                const SizedBox(height: 20),
                _buildSectionHeader("AGRICULTURAL INPUT"),
                Card(
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: BorderSide(color: Colors.grey.shade300),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: TextFormField(
                      controller: _pesticideController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: 'Pesticides Used',
                        suffixText: 'tonnes',
                        border: OutlineInputBorder(),
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
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _submitForm,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Theme.of(context).primaryColor,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
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
                const SizedBox(height: 24),
                AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  curve: Curves.easeInOut,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: _errorMessage != null
                        ? Colors.red.shade50
                        : (_predictionResult != null ? Colors.green.shade50 : Colors.grey.shade100),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: _errorMessage != null
                          ? Colors.red.shade200
                          : (_predictionResult != null ? Colors.green.shade200 : Colors.grey.shade300),
                    ),
                  ),
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      if (_errorMessage == null && _predictionResult == null)
                        const Text(
                          "Prediction result will appear here",
                          style: TextStyle(color: Colors.black54),
                        ),
                      if (_errorMessage != null)
                        Column(
                          children: [
                            const Icon(Icons.error_outline, color: Colors.red, size: 32),
                            const SizedBox(height: 8),
                            Text(
                              _errorMessage!,
                              style: TextStyle(color: Colors.red.shade900, fontWeight: FontWeight.w500),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      if (_predictionResult != null)
                        Column(
                          children: [
                            const Icon(Icons.check_circle_outline, color: Colors.green, size: 32),
                            const SizedBox(height: 8),
                            const Text(
                              "Estimated Yield",
                              style: TextStyle(fontSize: 14, color: Colors.black54),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              _predictionResult!,
                              style: TextStyle(
                                fontSize: 22,
                                fontWeight: FontWeight.bold,
                                color: Colors.green.shade900,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
