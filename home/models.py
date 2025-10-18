from django.db import models

class Banner(models.Model):
    BANNER_POSITIONS = [
        ('main', 'Main Banner'),
        ('secondary', 'Secondary Banner'),
        ('promotional', 'Promotional Banner'),
    ]
    
    image = models.ImageField(upload_to='banners/')
    position = models.CharField(max_length=20, choices=BANNER_POSITIONS, default='main')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['position', '-created_at']
    
    def __str__(self):
        return f"{self.get_position_display()} - {self.created_at.strftime('%Y-%m-%d')}"
    
    @classmethod
    def get_active_banners(cls):
        """Get one active banner for each position (main, secondary, promotional)"""
        banners = []
        for position, _ in cls.BANNER_POSITIONS:
            banner = cls.objects.filter(is_active=True, position=position).first()
            if banner:
                banners.append(banner)
        return banners