import rasterio, numpy as np
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine
from scipy.ndimage import binary_dilation
tr=Affine(50,0,563830,0,-50,1891320); sh=(2003,2144)
s=rasterio.open('../gsw_occurrence_delta.tif')
dst=np.zeros(sh,np.uint8)
reproject(rasterio.band(s,1),dst,dst_transform=tr,dst_crs='EPSG:32644',resampling=Resampling.max)
pw=dst>=90
pw=binary_dilation(pw,iterations=1)
np.save('/tmp/F/jrc_mask.npy',pw)
print(pw.mean(), (dst>=90).mean(), dst.max())
