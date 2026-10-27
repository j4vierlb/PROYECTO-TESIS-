import 'package:flutter/material.dart';

/// Mismo archivo de marca para Android e iOS; no se redibuja ni recorta el logo.
class CompanyLogo extends StatelessWidget {
  static const asset = 'assets/images/logo.png';
  static const label = 'Kill Bichos, control de plagas';
  final double size;

  const CompanyLogo({super.key, this.size = 32});

  @override
  Widget build(BuildContext context) => Image.asset(
    asset,
    width: size,
    height: size,
    fit: BoxFit.contain,
    semanticLabel: label,
  );
}

/// Mantiene el título de cada pantalla junto a la marca, incluso en ancho pequeño.
class CompanyTitle extends StatelessWidget {
  final String title;

  const CompanyTitle(this.title, {super.key});

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      const CompanyLogo(),
      const SizedBox(width: 12),
      Flexible(
        child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis),
      ),
    ],
  );
}
