# Agrega al Tema un velo opcional y configurable sobre la foto del sidebar.
#
# Antes, la imagen siempre se teñía con color_principal usando
# background-blend-mode: overlay, lo que le daba un tinte azulado. Con estos
# campos el velo pasa a ser una capa semitrtransparente normal (sin mezcla) y
# arranca en 0.00, es decir foto limpia: la legibilidad la resuelven la sombra
# en capas del texto y el chip translúcido del menú.
#
# Nota: usar_filtro_oscuro se conserva en el modelo por compatibilidad de
# datos, pero ya no controla el velo.
from decimal import Decimal

import colorfield.fields
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0076_alta_provisional_vacante_definitiva_99'),
    ]

    operations = [
        migrations.AddField(
            model_name='tema',
            name='color_velo',
            field=colorfield.fields.ColorField(
                default='#000000',
                help_text='Se aplica como una capa semitransparente sobre la imagen, sin mezclarse con ella. No altera los colores de la foto.',
                verbose_name='Color del Velo sobre la Foto'),
        ),
        migrations.AddField(
            model_name='tema',
            name='opacidad_velo',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='De 0.00 (foto limpia, sin velo) a 1.00 (velo totalmente opaco).',
                max_digits=3,
                validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('1.00'))],
                verbose_name='Opacidad del Velo'),
        ),
    ]