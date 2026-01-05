"""
Sistema de animaciones para la interfaz.
Solo animaciones de posición y tamaño (sin opacidad para evitar errores QPainter).
"""
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QSize, QRect


class AnimationMixin:
    """Mixin que provee métodos de animación para widgets."""
    
    def slide_in(self, from_direction="right", duration=300):
        """Animar entrada deslizando desde una dirección."""
        if not hasattr(self, '_slide_anim'):
            self._slide_anim = None
            
        current_pos = self.pos()
        parent = self.parent()
        
        if from_direction == "right":
            start = QPoint(parent.width() if parent else 800, current_pos.y())
        elif from_direction == "left":
            start = QPoint(-self.width(), current_pos.y())
        elif from_direction == "top":
            start = QPoint(current_pos.x(), -self.height())
        else:  # bottom
            start = QPoint(current_pos.x(), parent.height() if parent else 600)
        
        self.move(start)
        self.show()
        
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(duration)
        self._slide_anim.setStartValue(start)
        self._slide_anim.setEndValue(current_pos)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim.start()
        
        return self._slide_anim
    
    def slide_out(self, to_direction="right", duration=250, on_finished=None):
        """Animar salida deslizando hacia una dirección."""
        if not hasattr(self, '_slide_out_anim'):
            self._slide_out_anim = None
            
        current_pos = self.pos()
        parent = self.parent()
        
        if to_direction == "right":
            end = QPoint(parent.width() if parent else 800, current_pos.y())
        elif to_direction == "left":
            end = QPoint(-self.width(), current_pos.y())
        elif to_direction == "top":
            end = QPoint(current_pos.x(), -self.height())
        else:  # bottom
            end = QPoint(current_pos.x(), parent.height() if parent else 600)
        
        self._slide_out_anim = QPropertyAnimation(self, b"pos")
        self._slide_out_anim.setDuration(duration)
        self._slide_out_anim.setStartValue(current_pos)
        self._slide_out_anim.setEndValue(end)
        self._slide_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        
        if on_finished:
            self._slide_out_anim.finished.connect(on_finished)
        
        self._slide_out_anim.start()
        
        return self._slide_out_anim
    
    def bounce(self, intensity=10, duration=400):
        """Efecto de rebote."""
        if not hasattr(self, '_bounce_anim'):
            self._bounce_anim = None
            
        original_pos = self.pos()
        
        self._bounce_anim = QPropertyAnimation(self, b"pos")
        self._bounce_anim.setDuration(duration)
        self._bounce_anim.setKeyValueAt(0, original_pos)
        self._bounce_anim.setKeyValueAt(0.3, QPoint(original_pos.x(), original_pos.y() - intensity))
        self._bounce_anim.setKeyValueAt(0.6, QPoint(original_pos.x(), original_pos.y() + intensity // 2))
        self._bounce_anim.setKeyValueAt(1, original_pos)
        self._bounce_anim.setEasingCurve(QEasingCurve.Type.OutBounce)
        self._bounce_anim.start()
        
        return self._bounce_anim


class PageTransition:
    """Maneja transiciones entre páginas/widgets."""
    
    @staticmethod
    def slide_horizontal(stack_widget, new_index, direction="left", duration=300):
        """Transición horizontal entre páginas de un QStackedWidget."""
        current = stack_widget.currentWidget()
        new_widget = stack_widget.widget(new_index)
        
        if current == new_widget:
            return
        
        # Simplemente cambiar la página sin animación
        stack_widget.setCurrentIndex(new_index)
    
    @staticmethod
    def crossfade(stack_widget, new_index, duration=200):
        """Transición de crossfade entre páginas."""
        # Sin animación de opacidad para evitar errores QPainter
        stack_widget.setCurrentIndex(new_index)
